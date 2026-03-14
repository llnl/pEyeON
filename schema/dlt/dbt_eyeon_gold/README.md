# dbt: Gold Models (DuckDB)

This dbt project builds the Gold layer from the existing `silver` schema in
`schemas/eyeon_metadata.duckdb`.

## Install

From the repo root (or anywhere), install dbt for DuckDB:

```bash
python -m pip install -r schema/dlt/requirements-dbt.txt
```

## Run

Run dbt pointing at the local `profiles.yml` in this folder:

```bash
dbt build \
  --project-dir schema/dlt/dbt_eyeon_gold \
  --profiles-dir schema/dlt/dbt_eyeon_gold
```

Gold tables are created in the `gold` schema inside `schemas/eyeon_metadata.duckdb`.
