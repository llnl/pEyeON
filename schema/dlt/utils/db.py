import streamlit as st
import duckdb
import dlt
import utils.schema_ext as schema_ext
from pathlib import Path

def db_path():
    "TODO: pull from TOML file"
    return "schemas/eyeon_metadata.duckdb"

def exists()-> bool:
    return Path(db_path()).exists()

@st.cache_resource
def get_conn(schema="silver"):
    """
    Returns a cached DB connection shared across all pages and reruns.
    cache_resource keeps this alive for the lifetime of the app session.
    Silver is the default as it is generally used the most.
    """
    conn = duckdb.connect(db_path())
#    conn.execute(f"use {schema}")
    return conn

def init():
    "Initialize a new database instance."
    # Get db conn...
    sql_file = "schemas/schema.sql"

    con = duckdb.connect(db_path())

    with open(sql_file, "r", encoding="utf-8") as f:
        ddl_sql = f.read()
    statements = con.extract_statements(ddl_sql)
    for statement in statements:
        con.execute(statement)
    con.close()

# Load schema (cached)
@st.cache_resource
def get_schema():
    # Attaching to the pipeline gives us access to the file-based metadata DLT manages, such as the most current schema.
    pipeline = dlt.attach(pipeline_name="eyeon_metadata")
    schema = schema_ext.build_schema(pipeline,"schemas/eyeon_schema_overlay.yaml")
    return schema