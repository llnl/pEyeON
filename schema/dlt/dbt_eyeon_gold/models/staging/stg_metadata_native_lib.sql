select * from {{ source('silver', 'metadata_native_lib_file') }}
