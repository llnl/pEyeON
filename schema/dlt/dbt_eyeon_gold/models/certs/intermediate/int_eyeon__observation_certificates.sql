select
  s.observation_uuid,
  s.utility_id,
  s.batch_id,
  o.observation_ts,
  o.filename,
  o.source_path,
  o.source_file,
  o.file_sha256,
  s.cert_sha256,
  s.issuer_sha256,
  s.issuer_name,
  s.subject_name,
  s.issued_on,
  s.expires_on,
  s.signed_using,
  s.rsa_key_size,
  s.basic_constraints,
  s.key_usage,
  s.ext_key_usage,
  s.certificate_policies,
  s.serial_number,
  s.signers,
  s.digest_algorithm,
  s.verification,
  s.signature_sha1
from {{ ref('stg_eyeon__sigs_n_certs') }} s
left join {{ ref('stg_eyeon__observations') }} o
  on s.observation_uuid = o.observation_uuid
