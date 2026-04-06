from pages._base_page import BasePageLayout
from pages.pages import app_pages
import utils.db as db
from utils.utils import sidebar_config, list_all_batches, load_me_some_data
from utils.config import settings
import streamlit as st

import pandas as pd

class LandingPage(BasePageLayout):
    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(
            page_icon=settings.app.logo, page_title="EyeOn Summary", layout="wide"
        )
        sidebar_config(app_pages())
        st.header("EyeOn Summary")

        with st.expander("Loaded Data", expanded=True):
            # Hosts, labels, etc over time. Produces a constant vertical size, so its a good default for any size data set
            try:
                batches = (
                    db.get_conn()
                    .sql("from gold.batch_summary order by utility_id")
                    .df()
                )
            except Exception as e:
                st.warning("Batch summary is not available yet.")
                st.caption(f"{type(e).__name__}: {e}")
                batches = pd.DataFrame()

            if batches.empty:
                st.info("No batch summary rows found in `gold.batch_summary`.")
            else:
                tabs = st.tabs(["Dashboard", "Table"])

                total_utilities = int(batches["utility_id"].nunique())
                total_batches = int(batches["num_batches"].fillna(0).sum())
                total_obs = int(batches["num_rows"].fillna(0).sum())

                with tabs[0]:
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Utilities", f"{total_utilities}")
                    k2.metric("Batches", f"{total_batches}")
                    k3.metric("Observations", f"{total_obs}")
                    total_md_types=-1
                    k4.metric("Metadata Types", f"{total_md_types}")

                    left, right = st.columns([2, 1])
                    with left:
                        st.subheader("By Utility")
                        chart_tabs = st.tabs(
                            [
                                "Observations",
                                "Batches",
                                "Metadata Count"
                            ]
                        )

                        with chart_tabs[0]:
                            obs_df = batches[["utility_id", "num_rows"]].copy()
                            obs_df["num_rows"] = obs_df["num_rows"].fillna(0)
                            obs_df = obs_df.set_index("utility_id")
                            st.bar_chart(obs_df, height=260)

                        with chart_tabs[1]:
                            b_df = batches[["utility_id", "num_batches"]].copy()
                            b_df["num_batches"] = b_df["num_batches"].fillna(0)
                            b_df = b_df.set_index("utility_id")
                            st.bar_chart(b_df, height=260)

                        with chart_tabs[2]:
                            md_df = batches[["utility_id", "num_md_types"]].copy()
                            md_df["num_md_types"] = md_df["num_md_types"].fillna(0)
                            md_df = md_df.set_index("utility_id")
                            st.bar_chart(md_df, height=260)

                    with right:
                        st.subheader("Utility Details")
                        utilities = batches["utility_id"].astype(str).tolist()
                        selected_utility = st.selectbox(
                            "Utility",
                            utilities,
                            index=0,
                            key="summary_selected_utility",
                        )
                        row = batches.loc[
                            batches["utility_id"].astype(str) == selected_utility
                        ]
                        if not row.empty:
                            r0 = row.iloc[0]
                            m1, m2, m3 = st.columns(3)
                            m1.metric(
                                "Batches",
                                f"{int(r0.get('num_batches', 0) or 0)}",
                            )
                            m2.metric("Obs", f"{int(r0.get('num_rows', 0) or 0)}")
                            m3.metric(
                                "MD Types",
                                f"{int(r0.get('num_md_types', 0) or 0)}",
                            )

                with tabs[1]:
                    st.dataframe(batches, width="stretch", hide_index=True)

        with st.expander("All Batches", expanded=True):
            batch_dirs = list_all_batches(settings.datasets.dataset_path)

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
