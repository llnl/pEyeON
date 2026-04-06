import streamlit as st

from box.box_auth import authenticate_oauth
from box.box_config import get_box_settings
from eyeon import upload

settings = get_box_settings()

client = authenticate_oauth(settings)

folder = client.folder(settings.FOLDER)
box_files = upload.list_box_items()

st.title(f"Files and Folders in Box for {folder.get().name} ({settings.FOLDER})")
st.table(box_files)
