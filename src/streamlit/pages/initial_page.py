import common.page_frags as pf
from pages._base_page import BasePageLayout
from pages.pages import app_pages
from common.utils import sidebar_config
from utils.config import settings
import streamlit as st
import common.dqautil as du
import altair as alt


class LandingPage(BasePageLayout):
    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(
            page_icon=settings.app.logo, page_title="Observations Summary", layout="wide"
        )
        sidebar_config(app_pages())
        st.header("Summary info for current Observations")
        pf.summary()

        st.markdown("Observations Clustered by Time")
        obs_times_df = du.getdatafor(du.getcon(), "observation_times")
        st.bar_chart(obs_times_df, x="ObsTime", y="NumRows")
        st.dataframe(obs_times_df)

        ## detect it easy
        st.markdown("Detect it Easy")
        die_df = du.getdatafor(du.getcon(), "detect_it_easy")
        st.altair_chart(
            alt.Chart(die_df)
            .mark_bar()
            .encode(
                x=alt.X("detect_it_easy", sort=None),
                y="NumRows",
            )
            .interactive(),
            use_container_width=True,
        )

        # Proof-of-life debug info
        pf.debug_info()


def main():
    page = LandingPage()
    page.page_content()


if __name__ == "__main__":
    main()
