select
  time_bucket(interval '1 year', expires_on) as expiry_year,
  count(*) as expiring_certs
from {{ ref('dim_certificates') }}
where expires_on is not null
group by expiry_year
