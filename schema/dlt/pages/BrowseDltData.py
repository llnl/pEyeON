from pages._base_page import BasePageLayout
from  pages.pages import app_pages
from utils.utils import sidebar_config
import streamlit as st
import pandas as pd
import os
import utils.schema_ext as schema_ext
from utils.schema_ext import EnrichedTable
import utils.db as db
import duckdb


class LandingPage(BasePageLayout):
    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(layout="wide")
        sidebar_config(app_pages())

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
                    filter_metadata = st.selectbox("Metadata Type", ['all','elf','java','mach_o','native_lib','ole','pe','unknown'])
                    # Find an example file. Present a list of metadata types (that exist in this dataset) and then randomly pick one.
                    if filter_text:
                        sql = f"SELECT * FROM {table_name} WHERE {table.search_field} ILIKE ? ORDER BY {table.search_field}"
                        results = db.get_conn().execute(
                            sql,
                            [f"%{filter_text.replace('*', '%') }%"]
                        ).df()
                    elif filter_metadata:
                        md_table = f'metadata_{filter_metadata}_file'
                        if filter_metadata=='unknown':
                            sql='''
                            select o.* from silver.raw_obs o 
                            where o.uuid in (
                            select uuid from silver.metadata_elf_file
                            union all
                            select uuid from silver.metadata_java_file
                            union all
                            select uuid from silver.metadata_mach_o_file
                            union all
                            select uuid from silver.metadata_native_lib_file
                            union all
                            select uuid from silver.metadata_ole_file
                            union all
                            select uuid from silver.metadata_pe_file
                            )
                            '''                            
                            # filter OUT the unknowns...
                            results = db.get_conn().execute(sql).df()
                        elif filter_metadata=='all':
                            results = db.get_conn().execute(f"SELECT * FROM {table_name}").df()
                        else:
                            filter = 'm.uuid is not null'
                            results = db.get_conn().execute(f'select o.* from {table_name} o left outer join {md_table} m on m.uuid=o.uuid where {filter}').df()
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
                        try:
                            results = db.get_conn().execute(
                                f"SELECT * FROM {table_name}"
                            ).df()
                        except duckdb.CatalogException as e:
                            st.write(f"Table not found! Wrong schema? TODO: provide a button here to set the schema")
                            results = pd.DataFrame()
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
                width='stretch',
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

            "Should add something for this page here..."
            
        # Main content area
        if st.session_state.root_table_selector:
            render_table_level(db.get_schema().get_table(st.session_state.root_table_selector), level=0, key_prefix="root")
        else:
            st.info("Select a root table from the sidebar")

        # Footer showing current selection path
        if st.session_state.selections:
            st.divider()
            st.caption("Current Selection Path:")
            st.caption(" → ".join([f"{k}: {v[:20]}..." for k, v in st.session_state.selections.items()]))

def main():
    page = LandingPage()
    page.page_content()

if __name__ == "__main__":
    main()
