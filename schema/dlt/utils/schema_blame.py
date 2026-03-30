"""
schema_blame.py
===============
Tracks dlt schema evolution over time and links each change back to the
load and data rows that caused it — a "git blame" for your pipeline schema.

Data Flow
---------

```mermaid
flowchart TD
    A[_dlt_version\nJSON snapshots] -->|pairwise diff| B[extract_schema_changes\nPython diff logic]
    C[_dlt_loads\nepoch load_ids] -->|ASOF JOIN| D[enrich_with_load_ids\nSQL]
    B --> D
    D --> E[schema_blame\nDuckDB table]
    E -->|per change| F{change_type}
    F -->|new_column\ndropped_column\ntype_changed| G[trace_rows_for_change\ndata table query]
    F -->|new_table\ndropped_table| H[table-level summary only]
    G --> I[schema_blame_samples\nDuckDB table]
    E --> J[Streamlit / reporting layer]
    I --> J
```

Tables produced
---------------
- **schema_blame**         — one row per schema change event, with version, load_id, and detail
- **schema_blame_samples** — sampled rows from the data table that introduced each change

Incremental design
------------------
On each run, only schema versions not yet present in `schema_blame` are
processed. The high-water mark is read from the table itself, so the
function is safe to call repeatedly as a scheduled job.

Internal dlt tables and columns are excluded from all diffs.
"""

import json
import duckdb
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DLT_INTERNAL_TABLES = frozenset({
    "_dlt_version", "_dlt_loads", "_dlt_pipeline_state",
    "_dlt_load_ids", "_dlt_merge_keys",
})

DLT_INTERNAL_COLUMNS = frozenset({
    "_dlt_id", "_dlt_load_id", "_dlt_root_id", "_dlt_parent_id", "_dlt_list_idx",
})

SAMPLE_ROWS = 5  # rows captured per change event in schema_blame_samples


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SchemaChange:
    version_from:   int
    version_to:     int
    version_at:     str           # timestamp string from _dlt_version.inserted_at
    load_id:        Optional[str] # epoch string from _dlt_loads, set after enrichment
    change_type:    str           # see CHANGE_TYPES below
    table:          str
    column:         Optional[str]
    detail:         dict = field(default_factory=dict)

# change_type vocabulary:
#   new_table             — table appeared in schema for first time
#   dropped_table         — table removed from schema (data still in destination)
#   new_column            — column added to existing table
#   dropped_column        — column removed from schema
#   column_type_changed   — data_type widened or changed
#   column_nullable_changed


# ---------------------------------------------------------------------------
# Step 1: Diff adjacent schema versions
# ---------------------------------------------------------------------------

def _diff_columns(
    table_name: str,
    prev_cols: dict,
    curr_cols: dict,
    v_from: int,
    v_to: int,
    v_at,
) -> list[SchemaChange]:
    """Return SchemaChange records for column-level differences between two versions."""

    # strip internal dlt bookkeeping columns
    prev_cols = {k: v for k, v in prev_cols.items() if k not in DLT_INTERNAL_COLUMNS}
    curr_cols = {k: v for k, v in curr_cols.items() if k not in DLT_INTERNAL_COLUMNS}

    changes = []
    base = dict(version_from=v_from, version_to=v_to, version_at=v_at, load_id=None, table=table_name)

    for col in set(curr_cols) - set(prev_cols):
        changes.append(SchemaChange(**base, change_type="new_column", column=col,
                                    detail={"column_def": curr_cols[col]}))

    for col in set(prev_cols) - set(curr_cols):
        changes.append(SchemaChange(**base, change_type="dropped_column", column=col,
                                    detail={"column_def": prev_cols[col]}))

    for col in set(prev_cols) & set(curr_cols):
        p, c = prev_cols[col], curr_cols[col]

        if p.get("data_type") != c.get("data_type"):
            changes.append(SchemaChange(**base, change_type="column_type_changed", column=col,
                                        detail={"from": p.get("data_type"), "to": c.get("data_type")}))

        if p.get("nullable") != c.get("nullable"):
            changes.append(SchemaChange(**base, change_type="column_nullable_changed", column=col,
                                        detail={"from": p.get("nullable"), "to": c.get("nullable")}))

    return changes


def extract_schema_changes(conn: duckdb.DuckDBPyConnection, since_version: int = 0) -> list[SchemaChange]:
    """
    Walk _dlt_version pairwise and return all schema changes since `since_version`.
    Pass since_version from the high-water mark in schema_blame for incremental runs.
    """
    versions = conn.execute("""
        SELECT version, inserted_at, schema
        FROM _dlt_version
        WHERE version >= ?
        ORDER BY version
    """, [since_version]).fetchall()

    if len(versions) < 2:
        return []

    all_changes = []

    for i in range(1, len(versions)):
        v_from = versions[i-1][0]
        v_to, v_at = versions[i][0], versions[i][1]

        prev_tables = json.loads(versions[i-1][2]).get("tables", {})
        curr_tables = json.loads(versions[i][2]).get("tables", {})

        # filter dlt internals
        prev_tables = {k: v for k, v in prev_tables.items() if k not in DLT_INTERNAL_TABLES}
        curr_tables = {k: v for k, v in curr_tables.items() if k not in DLT_INTERNAL_TABLES}

        base = dict(version_from=v_from, version_to=v_to, version_at=v_at, load_id=None)

        for table in set(curr_tables) - set(prev_tables):
            all_changes.append(SchemaChange(**base, change_type="new_table", table=table, column=None,
                                            detail={"initial_columns": list(curr_tables[table].get("columns", {}).keys())}))

        for table in set(prev_tables) - set(curr_tables):
            all_changes.append(SchemaChange(**base, change_type="dropped_table", table=table, column=None))

        for table in set(prev_tables) & set(curr_tables):
            all_changes.extend(_diff_columns(
                table,
                prev_tables[table].get("columns", {}),
                curr_tables[table].get("columns", {}),
                v_from, v_to, v_at,
            ))

    return all_changes


# ---------------------------------------------------------------------------
# Step 2: Enrich changes with load_id via DuckDB ASOF JOIN
# ---------------------------------------------------------------------------

def enrich_with_load_ids(changes: list[SchemaChange], conn: duckdb.DuckDBPyConnection) -> list[SchemaChange]:
    """
    Use DuckDB's ASOF JOIN to find the load that immediately preceded each
    schema version timestamp — the causal load that triggered the change.

    ASOF JOIN semantics: for each row on the left, find the greatest
    right-side timestamp that is <= the left-side timestamp. This naturally
    expresses "which load happened just before this schema version was written."
    """
    if not changes:
        return changes

    # build a temp table from our change records so we can join in SQL
    changes_df = pd.DataFrame([
        {"version_to": c.version_to, "version_at": c.version_at}
        for c in changes
    ]).drop_duplicates()

    conn.register("_tmp_changes", changes_df)

    load_map = conn.execute("""
        SELECT
            c.version_to,
            l.load_id,
            to_timestamp(l.load_id::double) as load_ts
        FROM _tmp_changes c
        ASOF JOIN (
            SELECT load_id, to_timestamp(load_id::double) as load_ts
            FROM _dlt_loads
            WHERE status = 0
        ) l ON c.version_at >= l.load_ts
        ORDER BY c.version_to
    """).fetchall()

    conn.execute("DROP VIEW IF EXISTS _tmp_changes")

    version_to_load = {row[0]: row[1] for row in load_map}

    for change in changes:
        change.load_id = version_to_load.get(change.version_to)

    return changes


# ---------------------------------------------------------------------------
# Step 3: Trace rows in data tables back to each change
# ---------------------------------------------------------------------------

def trace_rows_for_change(change: SchemaChange, conn: duckdb.DuckDBPyConnection) -> Optional[pd.DataFrame]:
    """
    For column-level changes, return a sample of rows from the data table
    that were introduced by the responsible load. For new_column, we further
    filter to rows where the column is non-null — those are the first carriers.
    """
    if change.change_type not in ("new_column", "dropped_column", "column_type_changed", "column_nullable_changed"):
        return None
    if not change.load_id:
        return None

    # verify the table exists in the destination
    tables = conn.execute("SHOW TABLES").fetchall()
    if change.table not in {t[0] for t in tables}:
        return None

    where_extra = ""
    if change.change_type == "new_column":
        where_extra = f'AND "{change.column}" IS NOT NULL'

    try:
        return conn.execute(f"""
            SELECT * FROM "{change.table}"
            WHERE _dlt_load_id = ?
            {where_extra}
            LIMIT {SAMPLE_ROWS}
        """, [change.load_id]).fetchdf()
    except duckdb.Error:
        return None


# ---------------------------------------------------------------------------
# Step 4: Materialize to DuckDB tables (incremental)
# ---------------------------------------------------------------------------

DDL_SCHEMA_BLAME = """
CREATE TABLE IF NOT EXISTS schema_blame (
    version_from          INTEGER,
    version_to            INTEGER,
    version_at            TIMESTAMP,
    load_id               VARCHAR,
    change_type           VARCHAR,
    table_name            VARCHAR,
    column_name           VARCHAR,
    detail                JSON,
    processed_at          TIMESTAMP DEFAULT current_timestamp
)
"""

DDL_SCHEMA_BLAME_SAMPLES = """
CREATE TABLE IF NOT EXISTS schema_blame_samples (
    version_to            INTEGER,
    load_id               VARCHAR,
    table_name            VARCHAR,
    column_name           VARCHAR,
    change_type           VARCHAR,
    sample_row            JSON,
    processed_at          TIMESTAMP DEFAULT current_timestamp
)
"""


def get_high_water_mark(conn: duckdb.DuckDBPyConnection) -> int:
    """Return the highest version_to already processed, or 0 if table is empty."""
    result = conn.execute("SELECT MAX(version_to) FROM schema_blame").fetchone()
    return result[0] if result and result[0] is not None else 0


def materialize_schema_blame(conn: duckdb.DuckDBPyConnection) -> int:
    """
    Incremental materialization of schema_blame and schema_blame_samples.
    Returns the number of new change records written.
    """
    conn.execute(DDL_SCHEMA_BLAME)
    conn.execute(DDL_SCHEMA_BLAME_SAMPLES)

    since = get_high_water_mark(conn)
    changes = extract_schema_changes(conn, since_version=since)
    if not changes:
        print(f"schema_blame: no new changes since version {since}")
        return 0

    changes = enrich_with_load_ids(changes, conn)

    # write change records
    blame_rows = [
        {
            "version_from": c.version_from,
            "version_to":   c.version_to,
            "version_at":   c.version_at,
            "load_id":      c.load_id,
            "change_type":  c.change_type,
            "table_name":   c.table,
            "column_name":  c.column,
            "detail":       json.dumps(c.detail),
        }
        for c in changes
    ]
    conn.executemany("""
        INSERT INTO schema_blame
            (version_from, version_to, version_at, load_id, change_type, table_name, column_name, detail)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [list(r.values()) for r in blame_rows])

    # write row samples
    sample_count = 0
    for change in changes:
        df = trace_rows_for_change(change, conn)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO schema_blame_samples
                    (version_to, load_id, table_name, column_name, change_type, sample_row)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                change.version_to,
                change.load_id,
                change.table,
                change.column,
                change.change_type,
                json.dumps(row.to_dict(), default=str),
            ])
            sample_count += 1

    print(f"schema_blame: wrote {len(changes)} changes, {sample_count} sample rows (since version {since})")
    return len(changes)


# ---------------------------------------------------------------------------
# Convenience queries
# ---------------------------------------------------------------------------

def blame_summary(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """High-level changelog ordered by version."""
    return conn.execute("""
        SELECT
            version_from,
            version_to,
            version_at,
            load_id,
            change_type,
            table_name,
            column_name,
            detail
        FROM silver.schema_blame
        ORDER BY version_to, table_name, column_name
    """).fetchdf()


def print_blame_summary(conn: duckdb.DuckDBPyConnection) -> None:
    """Human-readable blame summary grouped by version transition and change type."""
    df = blame_summary(conn)
    if df.empty:
        print("No schema changes recorded.")
        return

    for (v_from, v_to, v_at), group in df.groupby(["version_from", "version_to", "version_at"], sort=True):
        load_id = group["load_id"].iloc[0]
        load_ts = pd.to_datetime(float(load_id), unit="s").strftime("%Y-%m-%d %H:%M:%S") if load_id else "unknown"
        print(f"\n{'='*70}")
        print(f"  Schema v{v_from} → v{v_to}   at {v_at}")
        print(f"  Load:  {load_id}  ({load_ts} UTC)")
        print(f"{'='*70}")

        for change_type, ct_group in group.groupby("change_type"):
            print(f"\n  [{change_type.upper()}]")
            for _, row in ct_group.iterrows():
                detail = json.loads(row["detail"]) if row["detail"] else {}
                if change_type == "new_table":
                    cols = detail.get("initial_columns", [])
                    # filter out dlt internals for readability
                    user_cols = [c for c in cols if c not in DLT_INTERNAL_COLUMNS]
                    print(f"    {row['table_name']}")
                    print(f"      columns ({len(user_cols)}): {', '.join(user_cols[:8])}", end="")
                    print(f"  ...+{len(user_cols)-8} more" if len(user_cols) > 8 else "")

                elif change_type == "new_column":
                    col_def = detail.get("column_def", {})
                    dtype   = col_def.get("data_type", "?")
                    nullable = "nullable" if col_def.get("nullable") else "not null"
                    print(f"    {row['table_name']}.{row['column_name']}  [{dtype}, {nullable}]")

                elif change_type == "column_type_changed":
                    print(f"    {row['table_name']}.{row['column_name']}  {detail.get('from')} → {detail.get('to')}")

                elif change_type == "column_nullable_changed":
                    print(f"    {row['table_name']}.{row['column_name']}  nullable: {detail.get('from')} → {detail.get('to')}")

                elif change_type in ("dropped_table", "dropped_column"):
                    col = f".{row['column_name']}" if row['column_name'] else ""
                    print(f"    {row['table_name']}{col}")

    print(f"\n{'='*70}")
    total = len(df)
    new_tables = len(df[df.change_type == "new_table"])
    new_cols   = len(df[df.change_type == "new_column"])
    print(f"  Total: {total} changes  ({new_tables} new tables, {new_cols} new columns)")
    print(f"{'='*70}\n")


def blame_for_column(table: str, column: str, conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Full blame history for a specific column, with sample rows."""
    return conn.execute("""
        SELECT
            b.version_to,
            b.version_at,
            b.load_id,
            b.change_type,
            b.detail,
            s.sample_row
        FROM silver.schema_blame b
        LEFT JOIN schema_blame_samples s
            ON  s.version_to  = b.version_to
            AND s.table_name  = b.table_name
            AND s.column_name = b.column_name
        WHERE b.table_name  = ?
          AND b.column_name = ?
        ORDER BY b.version_to
    """, [table, column]).fetchdf()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import dlt

    pipeline = dlt.attach(pipeline_name="eyeon_metadata")

    with pipeline.sql_client() as client:
        conn = client.native_connection  # raw DuckDB connection
        materialize_schema_blame(conn)
        print_blame_summary(conn)