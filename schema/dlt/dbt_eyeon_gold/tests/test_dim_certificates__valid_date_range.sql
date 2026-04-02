select *
from {{ ref('dim_certificates') }}
where issued_on is not null
  and expires_on is not null
  and issued_on > expires_on
