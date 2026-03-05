import streamlit as st
import duckdb
import dlt
import schema_ext

@st.cache_resource
def get_conn(db_path: str = "eyeon_metadata.duckdb"):
    """
    Returns a cached DB connection shared across all pages and reruns.
    cache_resource keeps this alive for the lifetime of the app session.
    """
    conn = duckdb.connect(db_path)
    return conn

# Load schema (cached)
@st.cache_resource
def get_schema():
    # Attaching to the pipeline gives us access to the file-based metadata DLT manages, such as the most current schema.
    pipeline = dlt.attach(pipeline_name="eyeon_metadata")
    schema = schema_ext.build_schema(pipeline,"schemas/eyeon_schema_overlay.yaml")
    return schema