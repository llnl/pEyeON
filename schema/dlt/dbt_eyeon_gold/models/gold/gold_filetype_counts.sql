with files as (
  select
    uuid,
    unnest(filetypes) as filetype
  from {{ ref('gold_files') }}
)

select
  filetype,
  count(*) as file_count,
  count(distinct uuid) as distinct_files
from files
group by 1
order by file_count desc
