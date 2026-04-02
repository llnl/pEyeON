select
  rsa_key_size,
  count(*) as num_keys
from {{ ref('dim_certificates') }}
group by rsa_key_size
