import streamlit as st
from utils.config import duckdb_path, resolve_dlt_path, settings, update_eyeondata_toml
import pages.pages as pages
import utils.db as db
from utils.schema_ext import EnrichedTable
from pathlib import Path
import os
import subprocess
import load_eyeon
from dbt.cli.main import dbtRunner, dbtRunnerResult
import pandas as pd
from datetime import datetime
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path



def app_base_config():
    st.set_page_config(
        # Page_title actually sets the tab name
        page_title=settings.app.page_title,
        initial_sidebar_state="expanded",
    )
    if db.exists():
        st.markdown("Virtual Main Page: Select a page from the sidebar!!")
    else:
        init_app_form()


def init_app_form():
    """
    If no existing database is found, prompt for an initial batch of data to load allow user to specify DB location.
    """
    with st.form(key="init_db_form"):
        st.markdown("Initialize Database")
        utility_id = st.text_input(
            "Utility ID",
            value=str(getattr(settings.defaults, "utility_id", "") or ""),
        )
        batch_dir = st.text_input(
            "Dataset Path",
            value=str(getattr(settings.datasets, "dataset_path", "") or ""),
            placeholder="/path/to/eyeon_json_data",
        )

        selected_rows = batch_selector()            

        database_path = st.text_input(
            "DB Directory path",
            value=str(getattr(settings.db, "db_path", "") or ""),
            placeholder="/path/to/database",
        )

        create_db_dir = st.checkbox(
            "Create DB directory if missing",
            value=False,
            help="If the directory does not exist, check this to allow the app to create it.",
        )

        submitted = st.form_submit_button("Submit")
        if submitted:
            errors: list[str] = []

            # Utility ID: required, string with no whitespace.
            utility_id_clean = (utility_id or "").strip()
            if not utility_id_clean:
                errors.append("Utility ID is required.")
            elif any(ch.isspace() for ch in utility_id_clean):
                errors.append("Utility ID must not contain spaces or other whitespace.")

            # JSON input directory: must exist and contain JSON files.
            batch_path = Path((batch_dir or "").strip()).expanduser()
            if not str(batch_path):
                errors.append("Dataset Path is required.")
            elif not batch_path.exists():
                errors.append(f"Dataset Path does not exist: {batch_path}")
            elif not batch_path.is_dir():
                errors.append(f"Dataset Path must be a directory: {batch_path}")

            # Must select at least 1 dataset dir
            if len(selected_rows)==0:
                errors.append("Must select at least 1 Dataset to process")

            # DB directory: create if requested; must end up writable.
            db_dir_path = Path((database_path or "").strip()).expanduser()
            if not str(db_dir_path):
                errors.append("DB Directory path is required.")
            elif db_dir_path.exists() and not db_dir_path.is_dir():
                errors.append(f"DB Directory path must be a directory: {db_dir_path}")

            if not errors:
                if not db_dir_path.exists():
                    if not create_db_dir:
                        errors.append(
                            f"DB Directory path does not exist: {db_dir_path}. Check 'Create DB directory if missing' to create it."
                        )
                    else:
                        try:
                            db_dir_path.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            errors.append(
                                f"Failed to create DB Directory path {db_dir_path}: {e}"
                            )

                if not errors:
                    if not db_dir_path.exists() or not db_dir_path.is_dir():
                        errors.append(
                            f"DB Directory path must be a directory: {db_dir_path}"
                        )
                    elif not os.access(str(db_dir_path), os.W_OK):
                        errors.append(
                            f"DB Directory path is not writable: {db_dir_path}"
                        )

            if errors:
                for msg in errors:
                    st.error(msg)
            else:
                # Persist to TOML so future runs pick these up as defaults.
                update_eyeondata_toml(
                    {
                        "db": {
                            "db_path": (database_path or "").strip(),
                        },
                        "defaults": {
                            "utility_id": utility_id_clean,
                            "json_dir": str(batch_path),
                        },
                    }
                )

                # Ensure the rest of this run uses the selected DB location.
                db_file = str(getattr(settings.db, "db_file", "eyeon.duckdb"))
                os.environ["EYEON_DUCKDB_PATH"] = str(
                    (resolve_dlt_path(db_dir_path) / db_file).resolve()
                )

                with st.spinner("Initializing..."):
                    db.init()
                    load_me_some_data(selected_rows)
#                    load_data(str(batch_path), utility_id=utility_id_clean)
                    run_dbt()

def batch_selector():
    with st.container(border=True):
        # Get OS Dirs
        batch_dirs = list_dirs(settings.datasets.dataset_path)

        event = st.dataframe(
            batch_dirs,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="dataset_dirs",
        )

        selected_rows: list[dict] = []
        if event.selection.rows:
            selected_rows = (
                batch_dirs.iloc[event.selection.rows]
                .copy()
                .replace({pd.NA: None})
                .to_dict(orient="records")
            )
        return selected_rows
    
# 20260326T153450Z_MAC -> ts=2026-03-26T15:34:50Z, utility_id=MAC
DIR_RE = re.compile(r"^(?P<ts>\d{8}T\d{6}Z)_(?P<utility_id>[^/]+)$")


@dataclass(frozen=True)
class BatchDir:
    path: Path
    utility_id: str
    ts_utc: datetime  # timezone-aware


def parse_batch_dir_name(name: str) -> tuple[datetime, str]:
    m = DIR_RE.match(name)
    if not m:
        raise ValueError(f"Unrecognized batch dir name: {name!r}")
    ts_utc = datetime.strptime(m.group("ts"), "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    utility_id = m.group("utility_id")
    return ts_utc, utility_id


def parse_batch_dir(path: str | Path) -> BatchDir:
    p = Path(path)
    ts_utc, utility_id = parse_batch_dir_name(p.name)
    return BatchDir(path=p, utility_id=utility_id, ts_utc=ts_utc)


def load_me_some_data(selected_rows: list[dict]) -> None:
    """Hook for loading selected batch rows"""
    with st.status("Processing data...", expanded=True) as status:
        for row in selected_rows:
            full_path = os.path.join(row["directory_path"], row["directory_name"])
            st.write(f"Loading using DLT: {full_path}")
            batch_info = parse_batch_dir(row["directory_name"])
            load_data(full_path, batch_info.utility_id)
        # DBT only needs to be run once for all batches
        st.write("Running DBT...")
        run_dbt()
        st.rerun()


def sidebar_config(pages):
    st.sidebar.image(settings.app.logo, width=120)
    st.sidebar.title(settings.app.page_title)
    st.sidebar.header("Menu")
    # Add pages that you want to expose on the sidebar here. They'll be listed in the order added.
    for page in pages:
        st.sidebar.page_link(page.filename, label=page.label)
    sidebar_db_chooser()


def _db_settings():
    schema_list = [
        s[0]
        for s in db.get_conn()
        .execute(
            "SELECT distinct schema_name FROM information_schema.schemata order by all"
        )
        .fetchall()
    ]

    # Schema selection inside the same expander context
    # Default to the "raw" schema
    cur_schema = st.selectbox(
        "Schema to use", schema_list, index=schema_list.index("silver")
    )

    if cur_schema is not None:
        db.get_conn().sql(f"use {cur_schema}")

    def _build_tree_md(table: EnrichedTable, depth: int = 0) -> list[str]:
        """Recursively build markdown lines for a table and its children."""
        indent = "  " * depth
        desc = f" — *{table.description}*" if table.description else ""
        col_count = len(table.columns)
        col_label = f"`{col_count} col{'s' if col_count != 1 else ''}`"
        lines = [f"{indent}- **{table.name}** {col_label}{desc}"]
        for child in sorted(table.get_children(), key=lambda t: t.name):
            lines.extend(_build_tree_md(child, depth + 1))
        return lines

    st.header("Tables")

    # Get root tables (tables with no parent)
    all_tables = db.get_schema().get_all_tables()
    root_tables = [
        name
        for name, defn in all_tables.items()
        if defn.get_parent() is None and not name.startswith("_dlt")
    ]

    selected_root = st.selectbox(
        "Select Root Table", sorted(root_tables), key="root_table_selector"
    )

    # --- In your expander ---
    with st.expander("Schema Info"):
        st.write(f"**Total Tables:** {len(all_tables)}")

        root_table = db.get_schema().get_table(selected_root)
        if root_table:
            st.markdown("**Table hierarchy:**")
            st.markdown("\n".join(_build_tree_md(root_table)))
    # Clear selections button
    if st.button("🔄 Clear All Selections"):
        st.session_state.selections = {}
        st.rerun()


def run_eyeon():
    with st.spinner("Running eyeon..."):
        try:
            # Run the command and capture the output
            command = f"../../builds/eyeon-parse.sh {settings.defaults.utility_id} {st.session_state.data_dir}"
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,  # Raise an exception if the command fails
                encoding="utf-8",
            )
            # Display the standard output in a code block
            st.subheader("Command Output")
            st.code(result.stdout, language="bash")

        except subprocess.CalledProcessError as e:
            # Display any errors if the command fails
            st.subheader("Error")
            st.error(f"Command failed with return code {e.returncode}:")
            st.code(e.stderr, language="bash")
        except Exception as e:
            # Handle other potential errors
            st.error(f"An unexpected error occurred: {e}")


def run_dbt():
    # Initialize the runner
    dbt = dbtRunner()

    # Ensure dbt points at the same DuckDB file as the app/DLT.
    os.environ["EYEON_DUCKDB_PATH"] = str(duckdb_path())

    # Define CLI arguments as a list of strings
    cli_args = [
        "run",
        "--project-dir",
        "dbt_eyeon_gold",
        "--profiles-dir",
        "dbt_eyeon_gold",
    ]

    # Invoke the command
    res: dbtRunnerResult = dbt.invoke(cli_args)

    # Inspect the results
    if res.success:
        for r in res.result:
            print(f"Node {r.node.name} finished with status: {r.status}")
    else:
        print("dbt execution failed.")


def load_data(batch_dir: str, utility_id=None):
    utility_id = utility_id or settings.defaults.utility_id
    load_eyeon.main(utility_id=utility_id, source=batch_dir)


def sidebar_db_chooser():
    if db.exists():
        with st.sidebar:
            _db_settings()


def list_dirs(directory_path: str) -> pd.DataFrame:
    empty_df = pd.DataFrame(columns=["directory_name", "modified_time"])
    rows = []

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    mtime_timestamp = entry.stat().st_mtime
                    mtime_readable = datetime.fromtimestamp(mtime_timestamp).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    rows.append(
                        {
                            "directory_path": directory_path,
                            "directory_name": entry.name,
                            "modified_time": mtime_readable,
                        }
                    )

        return pd.DataFrame(rows)

    except FileNotFoundError:
        print(f"Error: Directory not found at {directory_path}")
        return empty_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return empty_df


def list_all_batches(directory_path):
    all_batches_sql = """
    select b.*, d.*
    from silver.batch_info b
    full outer join dirs d on concat_ws('/',d.directory_path, d.directory_name)=regexp_replace(b.source, '/$', '')
    """
    dirs = list_dirs(directory_path)
    batches = db.get_conn().sql(all_batches_sql).df()
    return batches
