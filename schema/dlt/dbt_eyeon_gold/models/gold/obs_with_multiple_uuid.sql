{{ config(materialized='view') }}
select uuid, list(distinct _metadata_table_name) metadata_tables from {{ ref('all_metadata') }} o 
group by all
having count(*) > 1
