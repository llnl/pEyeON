select
  coalesce(subject_org, 'Empty') as organization,
  count(*) as num_rows
from {{ ref('dim_certificates') }}
group by coalesce(subject_org, 'Empty')
