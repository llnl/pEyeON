"""
schema_blame_ui.py
==================
Streamlit interface for exploring schema_blame data.

Run with:
    streamlit run schema_blame_ui.py
"""

import json
import dlt
import duckdb
import pandas as pd
import streamlit as st
import altair as alt
from schema_blame import (
    DLT_INTERNAL_COLUMNS,
    materialize_schema_blame,
    blame_summary,
    blame_for_column,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Schema Blame — eyeon_metadata",
    page_icon="🔬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Connection (cached so we don't reopen every rerun)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    pipeline = dlt.attach(pipeline_name="eyeon_metadata")
    client = pipeline.sql_client()
    client.__enter__()
    return client.native_connection


conn = get_connection()

# ---------------------------------------------------------------------------
# Sidebar — controls
# ---------------------------------------------------------------------------

st.sidebar.title("🔬 Schema Blame")
st.sidebar.caption("eyeon_metadata pipeline")

if st.sidebar.button("🔄 Refresh (run materialize)", use_container_width=True):
    n = materialize_schema_blame(conn)
    if n:
        st.sidebar.success(f"Wrote {n} new change(s)")
        st.cache_data.clear()
    else:
        st.sidebar.info("No new changes")

st.sidebar.divider()

change_type_options = [
    "new_table", "new_column", "dropped_table",
    "dropped_column", "column_type_changed", "column_nullable_changed"
]
selected_types = st.sidebar.multiselect(
    "Change types",
    options=change_type_options,
    default=change_type_options,
)

table_filter = st.sidebar.text_input("Filter by table name", placeholder="e.g. pe_file")

st.sidebar.divider()
st.sidebar.caption("Select a row in the changelog to drill into sample rows below.")

# ---------------------------------------------------------------------------
# Load blame data
# ---------------------------------------------------------------------------

@st.cache_data
def load_blame():
    return blame_summary(conn)

df_all = load_blame()

if df_all.empty:
    st.warning("No schema blame data found. Click **Refresh** in the sidebar to populate.")
    st.stop()

# apply filters
df = df_all[df_all["change_type"].isin(selected_types)]
if table_filter:
    df = df[df["table_name"].str.contains(table_filter, case=False, na=False)]

# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------

st.title("Schema Blame")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Schema versions", df_all["version_to"].nunique())
c2.metric("Total changes",   len(df_all))
c3.metric("New tables",      len(df_all[df_all.change_type == "new_table"]))
c4.metric("New columns",     len(df_all[df_all.change_type == "new_column"]))

st.divider()

# ---------------------------------------------------------------------------
# Version timeline — one expander per version transition
# ---------------------------------------------------------------------------

st.subheader("Changelog by version")

for (v_from, v_to), grp in df.groupby(["version_from", "version_to"], sort=True):
    v_at    = grp["version_at"].iloc[0]
    load_id = grp["load_id"].iloc[0]
    load_ts = pd.to_datetime(float(load_id), unit="s").strftime("%Y-%m-%d %H:%M:%S UTC") if load_id else "unknown"
    n_changes = len(grp)

    label = f"v{v_from} → v{v_to}   |   {v_at}   |   {n_changes} change(s)"
    with st.expander(label, expanded=(v_to == df["version_to"].max())):
        st.caption(f"Load ID: `{load_id}`  ({load_ts})")

        for ct, ct_grp in grp.groupby("change_type"):
            st.markdown(f"**{ct.replace('_', ' ').upper()}** ({len(ct_grp)})")

            for _, row in ct_grp.iterrows():
                detail = json.loads(row["detail"]) if row["detail"] else {}

                if ct == "new_table":
                    cols = detail.get("initial_columns", [])
                    user_cols = [c for c in cols if c not in DLT_INTERNAL_COLUMNS]
                    st.markdown(f"&nbsp;&nbsp;📋 `{row['table_name']}`  — {len(user_cols)} user columns")
                    st.code(", ".join(user_cols), language=None)

                elif ct == "new_column":
                    col_def  = detail.get("column_def", {})
                    dtype    = col_def.get("data_type", "?")
                    nullable = "nullable" if col_def.get("nullable") else "not null"
                    st.markdown(f"&nbsp;&nbsp;➕ `{row['table_name']}`.`{row['column_name']}`  [{dtype}, {nullable}]")

                elif ct == "column_type_changed":
                    st.markdown(
                        f"&nbsp;&nbsp;🔀 `{row['table_name']}`.`{row['column_name']}`  "
                        f"`{detail.get('from')}` → `{detail.get('to')}`"
                    )

                elif ct == "column_nullable_changed":
                    st.markdown(
                        f"&nbsp;&nbsp;🔀 `{row['table_name']}`.`{row['column_name']}`  "
                        f"nullable: `{detail.get('from')}` → `{detail.get('to')}`"
                    )

                elif ct in ("dropped_table", "dropped_column"):
                    col = f".`{row['column_name']}`" if row["column_name"] else ""
                    st.markdown(f"&nbsp;&nbsp;🗑️ `{row['table_name']}`{col}")

st.divider()

# ---------------------------------------------------------------------------
# Chart 1: Changes per version, stacked by change_type
# ---------------------------------------------------------------------------

st.subheader("Changes per version")

chart_df = (
    df_all.groupby(["version_to", "change_type"])
    .size()
    .reset_index(name="count")
)
chart_df["version_to"] = "v" + chart_df["version_to"].astype(str)

color_map = {
    "new_table":              "#4C9BE8",
    "new_column":             "#63C987",
    "dropped_table":          "#E8694C",
    "dropped_column":         "#E8A34C",
    "column_type_changed":    "#B07FE8",
    "column_nullable_changed":"#E8D44C",
}

bar = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("version_to:N", title="Schema version", sort=None),
        y=alt.Y("count:Q", title="Number of changes"),
        color=alt.Color(
            "change_type:N",
            scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
            legend=alt.Legend(title="Change type"),
        ),
        tooltip=["version_to", "change_type", "count"],
    )
    .properties(height=300)
)
st.altair_chart(bar, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Chart 2: Heatmap — which tables are changing most across versions
# ---------------------------------------------------------------------------

st.subheader("Table change heatmap")
st.caption("Darker = more changes in that version. Reveals which file types are still stabilizing.")

heat_df = (
    df_all.groupby(["version_to", "table_name"])
    .size()
    .reset_index(name="count")
)
heat_df["version_to"] = "v" + heat_df["version_to"].astype(str)

# strip leading "metadata_" for brevity
heat_df["table_short"] = heat_df["table_name"].str.replace(r"^metadata_", "", regex=True)

# order tables by total changes so the busiest rise to the top
table_order = (
    heat_df.groupby("table_short")["count"]
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

heatmap = (
    alt.Chart(heat_df)
    .mark_rect()
    .encode(
        x=alt.X("version_to:N", title="Schema version", sort=None),
        y=alt.Y("table_short:N", title="Table", sort=table_order),
        color=alt.Color(
            "count:Q",
            scale=alt.Scale(scheme="blues"),
            legend=alt.Legend(title="# changes"),
        ),
        tooltip=["table_name", "version_to", "count"],
    )
    .properties(height=max(200, len(table_order) * 22))
)
st.altair_chart(heatmap, use_container_width=True)

st.divider() # blame + sample rows for a specific column
# ---------------------------------------------------------------------------

st.subheader("Column drill-down")

all_tables = sorted(df_all["table_name"].dropna().unique())
col_tables  = st.selectbox("Table", options=[""] + all_tables)

if col_tables:
    col_cols = sorted(
        df_all[df_all["table_name"] == col_tables]["column_name"].dropna().unique()
    )
    if col_cols:
        selected_col = st.selectbox("Column", options=col_cols)

        if selected_col:
            drill = blame_for_column(col_tables, selected_col, conn)

            if drill.empty:
                st.info("No blame history found for this column.")
            else:
                for _, row in drill.iterrows():
                    st.markdown(
                        f"**v{row['version_to']}** &nbsp;·&nbsp; {row['version_at']} &nbsp;·&nbsp; "
                        f"`{row['change_type']}` &nbsp;·&nbsp; load `{row['load_id']}`"
                    )
                    if row.get("sample_row"):
                        sample = json.loads(row["sample_row"])
                        # show only non-null, non-internal fields
                        clean = {
                            k: v for k, v in sample.items()
                            if v is not None and k not in DLT_INTERNAL_COLUMNS
                        }
                        st.json(clean, expanded=False)
    else:
        st.info("No column-level changes recorded for this table.")