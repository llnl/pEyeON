from pages._base_page import BasePageLayout
from pages.pages import app_pages
import utils.db as db
from utils.utils import sidebar_config, list_all_batches, load_data, run_dbt
from utils.config import settings
import streamlit as st

import os
import pandas as pd


def load_me_some_data(selected_rows: list[dict]) -> None:
    """Hook for loading selected batch rows"""
    with st.status("Processing data...", expanded=True) as status:
        for row in selected_rows:
            full_path=os.path.join(row['directory_path'], row['directory_name'])
            st.write(f"Loading using DLT: {full_path}")
            load_data(full_path)
        # DBT only needs to be run once for all batches
        st.write("Running DBT...")
        run_dbt()
        st.rerun()


class LandingPage(BasePageLayout):
    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(
            page_icon="EyeOn_logo.png", page_title="EyeOn Summary", layout="wide"
        )
        sidebar_config(app_pages())
        st.header("EyeOn Summary")

        with st.expander("Loaded Data", expanded=True):
            # Hosts, labels, etc over time. Produces a constant vertical size, so its a good default for any size data set
            batches = (
                db.get_conn().sql("from gold.batch_summary order by utility_id").df()
            )
            st.dataframe(batches)

        with st.expander("All Batches", expanded=True):
            batch_dirs = list_all_batches("/Users/johnson30/data/eyeon/dev")

            event = st.dataframe(
                batch_dirs,
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
                key="all_batches_df",
            )

            selected_rows: list[dict] = []
            if event.selection.rows:
                selected_rows = (
                    batch_dirs.iloc[event.selection.rows]
                    .copy()
                    .replace({pd.NA: None})
                    .to_dict(orient="records")
                )

            if st.button(
                "Load Selected",
                disabled=len(selected_rows) == 0,
                help="Select one or more rows above to enable.",
            ):
                load_me_some_data(selected_rows)


def main():
    page = LandingPage()
    page.page_content()


if __name__ == "__main__":
    main()
