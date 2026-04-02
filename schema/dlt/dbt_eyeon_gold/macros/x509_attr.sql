{% macro x509_attr(column_name, key) -%}
  nullif(trim(regexp_extract({{ column_name }}, '(^|,[ ]*){{ key }}=([^,]+)', 2)), '')
{%- endmacro %}
