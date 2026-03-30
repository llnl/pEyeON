duckdb -f tmp/schema.sql schemas/eyeon_metadata.duckdb
python load_eyeon.py --utility_id CLI --source ~/data/eyeon/badstuff
python load_eyeon.py --utility_id CLI --source ~/data/eyeon/min_files_max_schema
dbt build --project-dir dbt_eyeon_gold/ --profiles-dir dbt_eyeon_gold  