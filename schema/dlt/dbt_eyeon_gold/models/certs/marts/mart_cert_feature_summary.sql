select
  is_ca,
  key_usage,
  ext_key_usage,
  count(*) as rows
from {{ ref('dim_certificates') }}
group by is_ca, key_usage, ext_key_usage
