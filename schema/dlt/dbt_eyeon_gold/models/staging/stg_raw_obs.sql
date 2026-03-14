with src as (
  select *
  from {{ source('silver', 'raw_obs') }}
)

select
  uuid,
  filename,
  cast(bytecount as bigint) as bytecount,
  magic,
  permissions,
  modtime,
  observation_ts,
  md5,
  sha1,
  sha256,
  ssdeep,
  telfhash,
  imphash,
  authentihash,
  authenticode_integrity,
  _dlt_load_id,
  _dlt_id as dlt_id
from src
