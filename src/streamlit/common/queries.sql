-- Dataset Summaries for Metrics

-- Cluster observations by time. Were you expecting many small clusters or a few large or ???
select
--# name: observation_times
time_bucket(INTERVAL '15 minutes', observation_ts) ObsTime, count(*) NumRows
from observations group by all order by all
;

select
--# name: observation_count
count(*) Observations from observations
;


-- Cluster and count detect_it_easy
SELECT 
--# name: detect_it_easy
LOWER(SUBSTRING(REGEXP_EXTRACT(detect_it_easy, '\.([^.]*)$'), 0)) detect_it_easy, count(*) NumRows
FROM observations group by all order by NumRows DESC LIMIT 30
;

-- Get raw data collection range, which means we need to ignore process data reconstructed from Windows logs, which are activitytype="refresh"
select
--# name: raw_data_range
	min(observation_ts) first_seen,
	max(observation_ts) last_seen,
from
	observations
;


-- Process centric metrics and analytics

-- Summarize processes by start/term
select 
--# name: process_life_summary
	process_life_cd,
	count(distinct process_name) uniq_process_name, 
	count(*) num_processes, 
    -- use window function to calculate the pct of grand total.
	(num_processes / sum(num_processes) over (partition by grouping(process_life_cd)))*100 pct,
from
	process_life_v1
group by rollup (process_life_cd)
order by all
;


-- Summarize processes by hostname, start/term
select 
--# name: process_life_host_summary
	hostname,
	process_life_cd,
	count(distinct process_name) uniq_process_name, 
	count(*) num_processes, 
	num_processes / sum(num_processes) over (partition by grouping(hostname, process_life_cd), hostname) pct_of_host,
from
	process_life_v1
group by
	rollup (hostname, process_life_cd)
order by all
;

-- Get count of unique process names
select 
--# name: uniq_process_count
  count(distinct process_name) uniq_count, count(*) total_processes
from process
;

-- Cluster observations with certificates by time.
select
--# name: cert_observation_times
time_bucket(INTERVAL '15 minutes', observation_ts) ObsTime, count(*) NumRows
from observations where ARRAY_LENGTH(signatures) > 0
group by all order by all
;

-- Count different RSA Key sizes
select
--# name: rsa_key_sizes
RSA_key_size, count(*) NumKeys from raw_uniq_certs group by all order by all
;

-- Cluster cert expiration times by year
select
--# name: expiration_years
time_bucket(INTERVAL '1 year', expires_on) ExpiryYear, count(*) "Expiring Certs"
from raw_uniq_certs group by all order by all
;

-- Cluster cert issued_on time by year
select
--# name: issue_years
time_bucket(INTERVAL '1 year', issued_on) IssueYear, count(*) "Issued Certs"
from raw_uniq_certs group by all order by all
;

-- Gets the state from the subject name
select 
--# name: subject_states
SUBSTRING(REGEXP_EXTRACT(subject_name, 'ST=([^,]+)'), 4) State, count(*) NumRows
FROM raw_uniq_certs group by all order by NumRows DESC
;

-- Gets the organization from the subject name
select 
--# name: organizations
SUBSTRING(REGEXP_EXTRACT(subject_name, 'O=([^,]+)'), 3) State, count(*) NumRows
FROM raw_uniq_certs group by all order by NumRows DESC
;

-- Get filesizes
select 
--# name: file_sizes
bytecount FROM observations
;

-- Cluter and count file extensions
SELECT 
--# name: file_extensions
LOWER(SUBSTRING(REGEXP_EXTRACT(filename, '\.([^.]*)$'), 0)) file_extension, count(*) NumRows
FROM observations group by all order by NumRows DESC LIMIT 30
;

-- Cluter magic bytes
SELECT 
--# name: magic_bytes
magic, count(*) NumRows
FROM observations group by all order by NumRows DESC LIMIT 30
;
