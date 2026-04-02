with ranked as (
  select
    cert_sha256,
    issuer_sha256,
    issuer_name,
    subject_name,
    issued_on,
    expires_on,
    signed_using,
    rsa_key_size,
    basic_constraints,
    key_usage,
    ext_key_usage,
    certificate_policies,
    serial_number,
    row_number() over (
      partition by cert_sha256
      order by observation_ts desc nulls last, observation_uuid
    ) as row_num
  from {{ ref('int_eyeon__observation_certificates') }}
)

select
  cert_sha256,
  issuer_sha256,
  issuer_name,
  subject_name,
  issued_on,
  expires_on,
  signed_using,
  rsa_key_size,
  basic_constraints,
  key_usage,
  ext_key_usage,
  certificate_policies,
  serial_number
from ranked
where row_num = 1
