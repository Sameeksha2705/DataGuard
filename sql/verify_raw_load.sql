-- DataGuard Raw Table Verification Queries

-- Check total number of rows loaded into raw_311_requests.
SELECT COUNT(*) AS total_raw_records
FROM raw_311_requests;


-- Preview first 5 records from the raw table.
SELECT *
FROM raw_311_requests
LIMIT 5;


-- Check sample complaint types loaded into PostgreSQL.
SELECT complaint_type, COUNT(*) AS complaint_count
FROM raw_311_requests
GROUP BY complaint_type
ORDER BY complaint_count DESC
LIMIT 10;


-- Check records by borough.
SELECT borough, COUNT(*) AS request_count
FROM raw_311_requests
GROUP BY borough
ORDER BY request_count DESC;