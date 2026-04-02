select
  o.uuid as observation_uuid,
  b.utility_id,
  o._dlt_load_id as batch_id,
  o.source_path,
  o.source_file,
  o.filename,
  o.observation_ts,
  o.sha256 as file_sha256,
  o.md5 as file_md5,
  o.sha1 as file_sha1,
  o.bytecount,
  o.magic,
  o.authentihash,
  o.imphash
from {{ source('silver', 'raw_obs') }} o
left join {{ source('silver', 'batch_info') }} b
  on b._dlt_load_id = o._dlt_load_id
