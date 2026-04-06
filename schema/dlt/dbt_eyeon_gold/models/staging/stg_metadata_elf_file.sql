select * from {{ source('silver', 'metadata_elf_file') }}
