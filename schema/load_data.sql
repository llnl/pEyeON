.read eyeon_ddl.sql

/** Partition files first:
select 'mkdir -p partitioned/pk_filetype\='||coalesce(filetype,'other')||' && cp '||json_filename||' partitioned/pk_filetype\='||coalesce(filetype,'other') from raw_json;
**/

create or replace view raw_json as from read_json('partitioned/**/*.json', union_by_name=true, sample_size = -1)
;
.read raw_base_metadata.sql

insert into observations by name 
  select * exclude (signatures, metadata) from raw_json
;
insert into base_metadata by name 
-- Dynamic list to account for any new Struct types in metadata.
-- Push this list down to the next inner query?
select * --exclude (FileInfo, aoutMachineType, EI_CLASS, binaries)
from 
  (select *,
    -- Return all fields
    -- Return just the subset that are known
    -- FileInfo.CompanyName,
    -- FileInfo.FileDescription,
    -- FileInfo.FileVersion,
    -- FileInfo.LegalCopyright,
    -- FileInfo.ProductName,
    -- FileInfo.ProductVersion
    from 
      (select * exclude (description, peMachine) from (select * from raw_base_metadata)))
;

insert into signatures by name
select signature_id:concat_ws(':',observation_uuid,sha1), * exclude (certs) 
from 
  (select observation_uuid:uuid, unnest(signatures, max_depth := 2) 
   from raw_json
  where len(signatures)>0
  )
;

insert into certificates by name
select signature_id:concat_ws(':',observation_uuid,sha1), "cert._version" cert_version, * 
  exclude ("observation_uuid", "signers", "digest_algorithm", "verification", "sha1", "cert._version", "subject_alt_name_:","directoryName")
from 
  (select 
    unnest(certs, recursive := true),
    * exclude (certs)
  from
    (select
  --   location_pk, batch_id, uuid,
        observation_uuid:uuid, unnest(signatures, recursive := true)
      from raw_json
      where len(signatures)>0
  )
)
;
