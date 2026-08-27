-- DataGuard SQL Business Queries
-- These queries analyze NYC 311 service request data loaded into PostgreSQL.

-- Query 1: Total number of raw service requests
SELECT COUNT(*) AS total_requests
FROM raw_311_requests;


-- Query 2: Top 10 complaint types
SELECT 
    complaint_type,
    COUNT(*) AS complaint_count
FROM raw_311_requests
GROUP BY complaint_type
ORDER BY complaint_count DESC
LIMIT 10;


-- Query 3: Requests by borough
SELECT 
    borough,
    COUNT(*) AS request_count
FROM raw_311_requests
GROUP BY borough
ORDER BY request_count DESC;


-- Query 4: Requests by status
SELECT 
    status,
    COUNT(*) AS status_count
FROM raw_311_requests
GROUP BY status
ORDER BY status_count DESC;


-- Query 5: Top 10 agencies by request volume
SELECT 
    agency,
    COUNT(*) AS request_count
FROM raw_311_requests
GROUP BY agency
ORDER BY request_count DESC
LIMIT 10;


-- Query 6: Top 10 cities by request volume
SELECT 
    city,
    COUNT(*) AS request_count
FROM raw_311_requests
GROUP BY city
ORDER BY request_count DESC
LIMIT 10;


-- Query 7: Top 10 descriptors
SELECT 
    descriptor,
    COUNT(*) AS descriptor_count
FROM raw_311_requests
GROUP BY descriptor
ORDER BY descriptor_count DESC
LIMIT 10;


-- Query 8: Noise complaints by borough
SELECT 
    borough,
    COUNT(*) AS noise_complaint_count
FROM raw_311_requests
WHERE complaint_type ILIKE '%noise%'
GROUP BY borough
ORDER BY noise_complaint_count DESC;


-- Query 9: Closed vs non-closed request count
SELECT 
    CASE 
        WHEN status = 'Closed' THEN 'Closed'
        ELSE 'Not Closed'
    END AS closure_group,
    COUNT(*) AS request_count
FROM raw_311_requests
GROUP BY closure_group
ORDER BY request_count DESC;


-- Query 10: Top complaint types in Brooklyn
SELECT 
    complaint_type,
    COUNT(*) AS complaint_count
FROM raw_311_requests
WHERE borough = 'BROOKLYN'
GROUP BY complaint_type
ORDER BY complaint_count DESC
LIMIT 10;