-- DataGuard Staging Table Verification Queries

-- Check total number of rows loaded into stg_311_requests.
SELECT COUNT(*) AS total_staged_records
FROM stg_311_requests;


-- Preview first 5 records from the staging table.
SELECT *
FROM stg_311_requests
LIMIT 5;


-- Check sample complaint types loaded into PostgreSQL.
SELECT complaint_type, COUNT(*) AS complaint_count
FROM stg_311_requests
GROUP BY complaint_type
ORDER BY complaint_count DESC
LIMIT 10;


-- Check records by borough.
SELECT borough, COUNT(*) AS request_count
FROM stg_311_requests
GROUP BY borough
ORDER BY request_count DESC;


-- Check load_id and loaded_at consistency for the most recent load.
SELECT load_id, loaded_at, COUNT(*) AS record_count
FROM stg_311_requests
GROUP BY load_id, loaded_at
ORDER BY loaded_at DESC;