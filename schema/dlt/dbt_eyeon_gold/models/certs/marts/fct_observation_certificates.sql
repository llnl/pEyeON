{{ config(materialized='table') }}

select
  observation_uuid,
  cert_sha256,
  utility_id,
  batch_id,
  observation_ts,
  filename,
  source_path,
  source_file,
  file_sha256,
  signers,
  digest_algorithm,
  verification,
  signature_sha1
from {{ ref('int_eyeon__observation_certificates') }}
