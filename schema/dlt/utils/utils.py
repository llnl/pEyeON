import streamlit as st
from utils.config import settings
import pages.pages as pages
import utils.db as db
from utils.schema_ext import EnrichedTable
from pathlib import Path
import os
import subprocess
import load_eyeon
from dbt.cli.main import dbtRunner, dbtRunnerResult


def app_base_config():
    st.set_page_config(
        # Page_title actually sets the tab name
        page_title=settings.app.page_title,
        initial_sidebar_state="expanded",
    )
    if db.exists():
        st.markdown("Virtual Main Page: Select a page from the sidebar!!")
    else:
        with st.form(key="init_db_form"):
            st.markdown("Initialize Database")
            batch_dir = st.text_input("Directory path", placeholder="/path/to/data")

            submitted = st.form_submit_button("Submit")
            if submitted:
                with st.spinner("Initializing..."):
                    db.init()
                    load_data(batch_dir)
                    run_dbt()

def sidebar_config(pages):
    st.sidebar.image("EyeOn_logo.png", width=120)
    st.sidebar.title(settings.app.page_title)
    st.sidebar.header("Menu")
    # Add pages that you want to expose on the sidebar here. They'll be listed in the order added.
    for page in pages:
        st.sidebar.page_link(page.filename, label=page.label)
    sidebar_db_chooser()

def _db_settings():
    schema_list = [s[0] for s in db.get_conn().execute(
        "SELECT distinct schema_name FROM information_schema.schemata order by all"
    ).fetchall()]

    # Schema selection inside the same expander context
    # Default to the "raw" schema
    cur_schema = st.selectbox("Schema to use", schema_list, index=schema_list.index('silver'))

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
    root_tables = [name for name, defn in all_tables.items()
            if defn.get_parent() is None and not name.startswith('_dlt')]
    
    selected_root = st.selectbox(
        "Select Root Table",
        sorted(root_tables),
        key="root_table_selector"
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
            command=f"../../builds/eyeon-parse.sh STREAMLIT {st.session_state.data_dir}"
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True, # Raise an exception if the command fails
                encoding='utf-8'
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

    # Define CLI arguments as a list of strings
    cli_args = ["run", "--project-dir", "dbt_eyeon_gold", "--profiles-dir", "dbt_eyeon_gold"]

    # Invoke the command
    res: dbtRunnerResult = dbt.invoke(cli_args)

    # Inspect the results
    if res.success:
        for r in res.result:
            print(f"Node {r.node.name} finished with status: {r.status}")
    else:
        print("dbt execution failed.")


def load_data(batch_dir):
#    args = ['--utility_id STREAMLIT', f'--source {batch_dir}']
    load_eyeon.main(utility_id='STREAMLIT', source=batch_dir)

def sidebar_db_chooser():
    if db.exists():
        with st.sidebar:
            _db_settings()


                
