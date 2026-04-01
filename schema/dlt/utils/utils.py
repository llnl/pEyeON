import streamlit as st
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
from utils.config import duckdb_path, resolve_dlt_path, settings


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
    with st.form(key="init_db_form"):
        st.markdown("Initialize Database")

        defaults_box = settings.get("defaults", {}) or {}
        db_box = settings.get("db", {}) or {}

        default_utility_id = str(defaults_box.get("utility_id", ""))
        default_json_dir = str(defaults_box.get("json_dir", ""))
        default_db_dir = str(db_box.get("db_path", "schemas"))

        utility_id = st.text_input("Utility ID", value=default_utility_id)
        batch_dir = st.text_input(
            "JSON Directory path",
            placeholder="/path/to/data",
            value=default_json_dir,
        )
        database_path = st.text_input(
            "DB Directory path",
            placeholder="/path/to/data",
            value=default_db_dir,
        )

        db_dir_preview = resolve_dlt_path(
            (database_path or "").strip() or default_db_dir
        )
        create_db_dir = False
        if not db_dir_preview.exists():
            st.warning(f"DB directory does not exist yet: {db_dir_preview}")
            create_db_dir = st.checkbox(
                "Create DB directory",
                value=False,
                help="Create this directory before initializing the database.",
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
                errors.append("JSON Directory path is required.")
            elif not batch_path.exists():
                errors.append(f"JSON Directory path does not exist: {batch_path}")
            elif not batch_path.is_dir():
                errors.append(f"JSON Directory path must be a directory: {batch_path}")
            elif not any(batch_path.glob("*.json")):
                errors.append(
                    f"No '*.json' files found in: {batch_path} (EyeOn loader reads only this directory, not subfolders)"
                )

            # DB directory: create if missing (with user confirmation), must end up writable.
            db_dir_path = resolve_dlt_path((database_path or "").strip())
            if not str(db_dir_path):
                errors.append("DB Directory path is required.")
            elif db_dir_path.exists() and not db_dir_path.is_dir():
                errors.append(f"DB Directory path must be a directory: {db_dir_path}")
            elif not db_dir_path.exists():
                if not create_db_dir:
                    errors.append(
                        "DB Directory path does not exist. Check 'Create DB directory' to create it."
                    )
                else:
                    parent = db_dir_path.parent
                    if not parent.exists():
                        errors.append(
                            f"Cannot create DB Directory path because parent does not exist: {parent}"
                        )
                    elif not os.access(str(parent), os.W_OK | os.X_OK):
                        errors.append(
                            f"Cannot create DB Directory path because parent is not writable: {parent}"
                        )
            elif not os.access(str(db_dir_path), os.W_OK | os.X_OK):
                errors.append(f"DB Directory path is not writable: {db_dir_path}")

            if errors:
                for msg in errors:
                    st.error(msg)
            else:
                # Apply overrides for this run (TOML on disk is unchanged).
                settings.set("db.db_path", str(db_dir_path))
                settings.set("defaults.utility_id", utility_id_clean)
                settings.set("defaults.json_dir", str(batch_path))

                if not db_dir_path.exists():
                    try:
                        db_dir_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        st.error(f"Failed to create DB directory {db_dir_path}: {e}")
                        return

                with st.spinner("Initializing..."):
                    db.init()
                    load_data(str(batch_path), utility_id=utility_id_clean)
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


def load_data(batch_dir, utility_id=None):
    #    args = ['--utility_id STREAMLIT', f'--source {batch_dir}']
    load_eyeon.main(
        utility_id=utility_id or settings.defaults.utility_id,
        source=batch_dir,
    )


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
