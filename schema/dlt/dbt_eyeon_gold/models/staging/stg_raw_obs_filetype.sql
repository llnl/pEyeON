select
  _dlt_root_id as dlt_root_id,
  value as filetype,
  _dlt_list_idx as filetype_idx
from {{ source('silver', 'raw_obs__filetype') }}
