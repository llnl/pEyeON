with files as (
  select *
  from {{ ref('stg_raw_obs') }}
),

batch as (
  select
    _dlt_load_id,
    run_ts,
    utility_id,
    source_path,
    depth,
    hostname
  from {{ ref('stg_batch_info') }}
),

filetypes as (
  select
    f.uuid,
    list(ft.filetype order by ft.filetype_idx) as filetypes
  from files f
  left join {{ ref('stg_raw_obs_filetype') }} ft
    on ft.dlt_root_id = f.dlt_id
  group by 1
),

latest as (
  select *
  from (
    select
      f.*,
      row_number() over (
        partition by f.uuid
        order by f.observation_ts desc nulls last, f.modtime desc nulls last, f._dlt_load_id desc
      ) as rn
    from files f
  )
  where rn = 1
)

select
  l.uuid,
  l.filename,
  regexp_extract(l.filename, '\\.([^.]+)$', 1) as file_ext,
  l.magic,
  l.bytecount,
  case
    when l.bytecount is null then null
    when l.bytecount < 1024 then cast(l.bytecount as varchar) || ' B'
    when l.bytecount < 1024 * 1024 then cast(round(l.bytecount / 1024.0, 2) as varchar) || ' KiB'
    when l.bytecount < 1024 * 1024 * 1024 then cast(round(l.bytecount / (1024.0 * 1024.0), 2) as varchar) || ' MiB'
    else cast(round(l.bytecount / (1024.0 * 1024.0 * 1024.0), 2) as varchar) || ' GiB'
  end as bytecount_human,
  l.permissions,
  l.modtime,
  l.observation_ts,
  l.md5,
  l.sha1,
  l.sha256,
  l.ssdeep,
  l.telfhash,
  l.imphash,
  l.authentihash,
  l.authenticode_integrity,
  b.utility_id,
  b.source_path,
  b.depth,
  b.hostname,
  b.run_ts as batch_run_ts,
  ft.filetypes,
  l._dlt_load_id
from latest l
left join batch b
  on b._dlt_load_id = l._dlt_load_id
left join filetypes ft
  on ft.uuid = l.uuid
