select
  utility_id as location,
  count(*) as num_rows
from {{ ref('fct_observation_certificates') }}
group by utility_id
