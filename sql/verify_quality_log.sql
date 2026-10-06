-- DataGuard Quality Log Verification Queries

-- Check how many quality checks were logged.
SELECT COUNT(*) AS total_quality_checks
FROM quality_log;


-- View all quality check results.
SELECT *
FROM quality_log
ORDER BY check_id;


-- View high-risk quality issues.
SELECT 
    check_name,
    issue_category,
    column_name,
    issue_count,
    severity,
    recommended_action
FROM quality_log
WHERE severity IN ('High', 'Critical')
ORDER BY issue_count DESC;


-- Count quality checks by severity.
SELECT 
    severity,
    COUNT(*) AS check_count
FROM quality_log
GROUP BY severity
ORDER BY check_count DESC;