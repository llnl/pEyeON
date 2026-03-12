import streamlit as st
import duckdb
import dlt
import utils.schema_ext as schema_ext

@st.cache_resource
def get_conn(db_path: str = "schemas/eyeon_metadata.duckdb", schema="silver"):
    """
    Returns a cached DB connection shared across all pages and reruns.
    cache_resource keeps this alive for the lifetime of the app session.
    Silver is the default as it is generally used the most.
    """
    conn = duckdb.connect(db_path)
    conn.execute(f"use {schema}")
    return conn

# Load schema (cached)
@st.cache_resource
def get_schema():
    # Attaching to the pipeline gives us access to the file-based metadata DLT manages, such as the most current schema.
    pipeline = dlt.attach(pipeline_name="eyeon_metadata")
    schema = schema_ext.build_schema(pipeline,"schemas/eyeon_schema_overlay.yaml")
    return schema