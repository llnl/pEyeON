with certs as (
  select *
  from {{ source('silver', 'raw_obs__signatures__certs') }}
),

signatures as (
  select *
  from {{ source('silver', 'raw_obs__signatures') }}
),

observations as (
  select
    uuid as observation_uuid,
    _dlt_id as observation_dlt_id,
    _dlt_load_id as batch_id
  from {{ source('silver', 'raw_obs') }}
),

batches as (
  select
    _dlt_load_id as batch_id,
    utility_id
  from {{ source('silver', 'batch_info') }}
)

select
  o.observation_uuid,
  b.utility_id,
  o.batch_id,
  c.sha256 as cert_sha256,
  c.issuer_sha256,
  c.issuer_name,
  c.subject_name,
  c.issued_on,
  c.expires_on,
  c.signed_using,
  c.rsa_key_size,
  c.basic_constraints,
  c.key_usage,
  c.ext_key_usage,
  c.certificate_policies,
  c.serial_number,
  s.signers,
  s.digest_algorithm,
  s.verification,
  s.sha1 as signature_sha1
from certs c
left join signatures s
  on s._dlt_id = c._dlt_parent_id
left join observations o
  on o.observation_dlt_id = c._dlt_root_id
left join batches b
  on b.batch_id = o.batch_id
where c.sha256 is not null
