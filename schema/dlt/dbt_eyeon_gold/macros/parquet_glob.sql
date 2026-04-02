{% macro parquet_glob(folder_name) -%}
  {{ return(var('eyeon_dataset_root') ~ '/' ~ folder_name ~ '/**/*.parquet') }}
{%- endmacro %}
