select
  coalesce(subject_state, 'Empty') as state,
  count(*) as num_rows
from {{ ref('dim_certificates') }}
group by coalesce(subject_state, 'Empty')
