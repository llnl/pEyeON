with src as (
  select *
  from {{ source('silver', 'batch_info') }}
)

select
  _dlt_load_id,
  run_ts,
  utility_id,
  source as source_path,
  depth,
  hostname,
  _dlt_id as dlt_id
from src
