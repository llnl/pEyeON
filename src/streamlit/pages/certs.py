import common.page_frags as pf
from pages._base_page import BasePageLayout
from pages.pages import app_pages
from common.utils import sidebar_config
from utils.config import settings
import pandas as pd
import streamlit as st
import common.dqautil as du
import altair as alt


class LandingPage(BasePageLayout):
    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(
            page_icon=settings.app.logo, page_title="Certificates Summary", layout="wide"
        )
        sidebar_config(app_pages())
        st.header("Certificate Data Visualization")
        # pf.summary()

        st.markdown("#### Observations Containing Certificates")
        obs_times_df = du.getdatafor(du.getcon(), "cert_observation_times")
        st.bar_chart(obs_times_df, x="ObsTime", y="NumRows")
        # st.dataframe(obs_times_df)

        st.markdown("#### Issuers")
        issuer_names_df = du.getdatafor(du.getcon(), "organizations")
        print(issuer_names_df)
        st.altair_chart(
            alt.Chart(issuer_names_df)
            .mark_arc()
            .encode(theta=alt.Theta("NumRows:Q").stack(True), 
                    radius=alt.Radius("NumRows").scale(type="sqrt", zero=True, rangeMin=20),
                    color="State:N",
            ),
            use_container_width=True,
        )

        st.markdown("#### RSA Key Sizes")
        key_sizes_df = du.getdatafor(du.getcon(), "rsa_key_sizes")
        # This horizontal barchart needs at least streamlit v1.36 I think
        # st.bar_chart(key_sizes_df, x="RSA_key_size", y="NumKeys", horizontal=True)
        st.altair_chart(
            alt.Chart(key_sizes_df)
            .mark_arc()
            .encode(theta=alt.Theta("NumKeys:Q"), color=alt.Color("RSA_key_size:N"))
            .interactive(),
            use_container_width=True,
        )

        st.markdown("#### Certificate Issue and Expiry Dates")
        exp_years_df = du.getdatafor(du.getcon(), "expiration_years")
        issue_years_df = du.getdatafor(du.getcon(), "issue_years")
        exp_years_df["Year"] = pd.DatetimeIndex(exp_years_df["ExpiryYear"]).year
        issue_years_df["Year"] = pd.DatetimeIndex(issue_years_df["IssueYear"]).year
        merged_df = pd.merge(issue_years_df, exp_years_df, how="outer", on="Year")
        merged_df["Expiring Certs"] = merged_df["Expiring Certs"] * -1  # to make bars diverge
        merged_df = merged_df.drop(columns=["ExpiryYear", "IssueYear"])
        merged_df = merged_df.melt("Year", var_name="type", value_name="Count")

        # st.altair_chart(alt.Chart(merged_df).mark_line().encode(
        #         x=alt.X('Year:O', axis=alt.Axis(format='d')),
        #         y=alt.Y('Count:Q', axis=alt.Axis()),
        #         color='type:N',
        #     ).interactive(),
        #     use_container_width=True
        # )

        st.altair_chart(
            alt.Chart(merged_df)
            .mark_bar()
            .encode(
                x=alt.X("Year:O", axis=alt.Axis(format="d")),
                y=alt.Y("Count:Q", axis=alt.Axis()),
                color="type:N",
            )
            .interactive(),
            use_container_width=True,
        )

        st.markdown("#### Certificate Locations")
        states_df = du.getdatafor(du.getcon(), "subject_states")
        states_df["State"] = states_df["State"].replace("", "Empty")
        st.bar_chart(states_df, x="State", y="NumRows")

        # Proof-of-life debug info
        pf.debug_info()


def main():
    page = LandingPage()
    page.page_content()


if __name__ == "__main__":
    main()
