{{ config(materialized='view') }}
select 
  b.utility_id, 
  count(distinct b._dlt_load_id) num_batches, 
  count(o.*) num_rows, 
  count(distinct md._metadata_table_name) num_md_types,
  list(distinct md._metadata_table_name) num_md_types
from {{ ref('stg_batch_info') }} b
left join {{ ref('stg_raw_obs') }} o on o._dlt_load_id=b._dlt_load_id
left outer join {{ 'all_metadata'}} md on md.uuid=o.uuid
group by all order by all
