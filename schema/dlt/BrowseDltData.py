import streamlit as st
import pandas as pd
import duckdb
import os
import schema_ext as schema_ext
import dlt
from schema_ext import EnrichedTable
import db


# Configure page
st.set_page_config(layout="wide")

def get_child_tables(table_name):
    """Get immediate child tables"""
    return db.get_schema().get_table(table_name).get_children()

def query_table(table_name, parent_row=None):
    """
    Query a table, optionally filtering by parent_id
    """
    parent_column="_dlt_parent_id"
    parent_id=None
    
    table = db.get_schema().get_table(table_name)

    results=None
    if parent_row is None:
        # Root level query
        if table.search_field:
            filter_text = st.text_input(
                f"🔍 Filter on: {table.search_field}", 
                placeholder="Use % or * for wildcard (case insensitive)"
            )
            # Find an example file. Present a list of metadata types (that exist in this dataset) and then randomly pick one.
            if filter_text:
                results = db.get_conn().execute(
                    f"SELECT * FROM {table_name} WHERE {table.search_field} ILIKE ? ORDER BY {table.search_field}",
                    [f"%{filter_text.replace('*', '%') }%"]
                ).df()
            else:
                results = db.get_conn().execute(
                    f"SELECT * FROM {table_name}"
                ).df()
        else:
            if any(col.extra.get("search") for col in table.columns.values()):
                search_cols={}
                for k,v in table.columns.items():
                    if v.extra.get("search"):
                        search_cols[k] = st.checkbox(f"{k} is null", False)
                filter = "true"
                for k,v in search_cols.items():
                    if v:
                        filter+=f" and {k} is null"
                results = db.get_conn().execute(f"select * from {table_name} where {filter}").df()                   
            else:
                results = db.get_conn().execute(
                    f"SELECT * FROM {table_name}"
                ).df()
    else:
        # Child query filtered by parent
        # TODO: 
        if table_name.startswith("metadata_") and "__" not in table_name:
            parent_column="uuid"
            parent_id=parent_row["uuid"]
        else:
            parent_column="_dlt_parent_id"
            parent_id=parent_row["_dlt_id"]
        results = db.get_conn().query(f"SELECT * FROM {table_name} WHERE {parent_column} = '{parent_id}' LIMIT 100").df()
    
    return results

def render_table_level(table:EnrichedTable, parent_row=None, level=0, key_prefix=""):
    """Recursively render table and its children"""
    # Query the data
    df = query_table(table.name, parent_row)
    
    if df.empty:
        if not hide_empty_tables:
            st.markdown(f"{'  ' * level}### {'📄' if level == 0 else '📋'} {table.name}")
            st.info(f"No data in {table.name}")
        return
    else:
        st.markdown(f"{'  ' * level}### {'📄' if level == 0 else '📋'} {table.name}")

    # Show dataframe with selection enabled
    selection_key = f"{key_prefix}_{table.name}_{level}"
    
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=selection_key
    )
    
    # Check if a row was selected
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_row = df.iloc[selected_idx]
        selected_id = selected_row['_dlt_id']
        
        # Store selection in session state
        st.session_state.selections[table.name] = selected_id
        
        if table.name=="json_errors":
            # Display an inspect button
            if st.button("Inspect File"):
                os.system(f"code {selected_row['_source_file']}")

        # Show selected row details
        with st.expander(f"🔍 Selected Row Details", expanded=False):
            st.json(selected_row.to_dict())
        
        # Get and render child tables
        children = get_child_tables(table.name)
        
        if children:
            with st.container(border=True):
                st.markdown(f"**Child Tables ({len(children)}):**")
                
                # Use columns for multiple children
                if len(children) <= 2:
                    cols = st.columns(len(children))
                    for idx, child in enumerate(children):
                        with cols[idx]:
                            render_table_level(
                                child, 
                                selected_row, 
                                level + 1,
                                key_prefix=f"{key_prefix}_{selected_id}"
                            )
                else:
                    # Stack vertically for many children
                    for child in children:
                        render_table_level(
                            child, 
                            selected_row, 
                            level + 1,
                            key_prefix=f"{key_prefix}_{selected_id}"
                        )
    else:
        # Clear selection if no row selected
        if table.name in st.session_state.selections:
            del st.session_state.selections[table.name]

# Main UI

# Initialize session state for tracking selections
if 'selections' not in st.session_state:
    st.session_state.selections = {}

    st.title("Master-Detail Schema Explorer")

hide_empty_tables = st.checkbox('Hide Empty Tables', True)

# Sidebar for table selection
with st.sidebar:

    st.subheader("Database")
    db_path = st.text_input("Database path:", "eyeon_metadata.duckdb")

    schema_list = [s[0] for s in db.get_conn().execute(
        "SELECT distinct schema_name FROM information_schema.schemata order by all"
    ).fetchall()]

    # Schema selection inside the same expander context
    # Default to the "raw" schema
    cur_schema = st.selectbox("Schema to use", schema_list, index=schema_list.index('raw'))

    if cur_schema is not None:
        db.get_conn().sql(f"use {cur_schema}")

    st.header("Tables")
    
    # Get root tables (tables with no parent)
    all_tables = db.get_schema().get_all_tables()
    root_tables = [name for name, defn in all_tables.items()
               if defn.get_parent() is None and not name.startswith('_dlt')]
    
    selected_root = st.selectbox(
        "Select Root Table",
        sorted(root_tables),
        key="root_table_selector"
    )
    
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

# Main content area
if selected_root:
    render_table_level(db.get_schema().get_table(selected_root), level=0, key_prefix="root")
else:
    st.info("Select a root table from the sidebar")

# Footer showing current selection path
if st.session_state.selections:
    st.divider()
    st.caption("Current Selection Path:")
    st.caption(" → ".join([f"{k}: {v[:20]}..." for k, v in st.session_state.selections.items()]))