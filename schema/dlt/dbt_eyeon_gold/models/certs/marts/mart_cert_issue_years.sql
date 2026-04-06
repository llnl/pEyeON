select
  time_bucket(interval '1 year', issued_on) as issue_year,
  count(*) as issued_certs
from {{ ref('dim_certificates') }}
where issued_on is not null
group by issue_year
