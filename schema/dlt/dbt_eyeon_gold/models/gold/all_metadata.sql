{{ config(materialized='view') }}
select uuid, _metadata_table_name from {{ ref('stg_metadata_elf_file') }}
union all
select uuid, _metadata_table_name from {{ ref('stg_metadata_java_file') }}
union all
select uuid, _metadata_table_name from {{ ref('stg_metadata_mach_o_file') }}
union all
select uuid, _metadata_table_name from {{ ref('stg_metadata_native_lib') }}
union all
select uuid, _metadata_table_name from {{ ref('stg_metadata_ole_file') }}
union all
select uuid, _metadata_table_name from {{ ref('stg_metadata_pe_file') }}
