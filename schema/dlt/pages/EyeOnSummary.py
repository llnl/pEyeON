from pages._base_page import BasePageLayout
from  pages.pages import app_pages
import utils.db as db
from utils.utils import sidebar_config
from utils.config import settings
import streamlit as st

import os

class LandingPage(BasePageLayout):

    def __init__(self):
        super().__init__()

    def page_content(self):
        st.set_page_config(page_icon="EyeOn_logo.png", page_title="EyeOn Summary", layout="wide")
        sidebar_config(app_pages())
        st.header("EyeOn Summary")

        with st.expander("batches", expanded=True):
            # Hosts, labels, etc over time. Produces a constant vertical size, so its a good default for any size data set
            batches = db.get_conn().sql('select b.*, count(o.*) filter (o.uuid is not null) Observations from silver.batch_info b left outer join silver.raw_obs o on o._dlt_load_id=b._dlt_load_id group by all order by b._dlt_load_id').df()
            st.dataframe(batches)

        

    
def main():
    page = LandingPage()
    page.page_content()

if __name__ == "__main__":
    main()
