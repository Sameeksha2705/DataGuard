-- DataGuard SQL-Based Quality Checks (Parameterized)
--
-- Defines a reusable function, run_quality_checks(target_table), that runs
-- the same set of data quality checks against either stg_311_requests or
-- clean_311_requests, tagging results with which table was checked.
--
-- Design notes:
-- 1. The function copies only the columns it needs into a fixed-name temp
--    table first, then runs one single, static set of checks against that
--    temp table. This keeps the "dynamic" part (which table to read from)
--    isolated to one line, instead of scattered through every check.
-- 2. target_table is validated against an explicit allow-list before being
--    used in dynamic SQL, to guard against SQL injection.
-- 3. Borough and status comparisons use UPPER() rather than exact case
--    matches, because the cleaning step uppercases text columns -- a check
--    written for 'Unspecified' would silently stop matching 'UNSPECIFIED'
--    in the clean table otherwise.
-- 4. Rows are no longer truncated between runs. Each run is tagged with
--    its own run_id and table_name, so quality_log now holds a running
--    history across runs instead of only the most recent one.

CREATE OR REPLACE FUNCTION run_quality_checks(target_table TEXT)
RETURNS UUID AS $$
DECLARE
    v_run_id UUID := gen_random_uuid();
BEGIN
    IF target_table NOT IN ('stg_311_requests', 'clean_311_requests') THEN
        RAISE EXCEPTION 'run_quality_checks: % is not an allowed table', target_table;
    END IF;

    DROP TABLE IF EXISTS tmp_quality_check_source;

    EXECUTE format(
        'CREATE TEMP TABLE tmp_quality_check_source AS
         SELECT
             unique_key,
             created_date,
             closed_date,
             complaint_type,
             borough,
             status,
             city,
             latitude,
             longitude
         FROM %I',
        target_table
    );

    WITH issue_counts AS (

        SELECT 'missing_unique_key' AS rule_code, COUNT(*) AS issue_count
        FROM tmp_quality_check_source
        WHERE unique_key IS NULL

        UNION ALL

        SELECT 'duplicate_unique_key', COUNT(*)
        FROM (
            SELECT unique_key
            FROM tmp_quality_check_source
            WHERE unique_key IS NOT NULL
            GROUP BY unique_key
            HAVING COUNT(*) > 1
        ) duplicate_keys

        UNION ALL

        SELECT 'missing_created_date', COUNT(*)
        FROM tmp_quality_check_source
        WHERE created_date IS NULL

        UNION ALL

        SELECT 'missing_complaint_type', COUNT(*)
        FROM tmp_quality_check_source
        WHERE complaint_type IS NULL

        UNION ALL

        SELECT 'missing_borough', COUNT(*)
        FROM tmp_quality_check_source
        WHERE borough IS NULL

        UNION ALL

        SELECT 'unspecified_borough', COUNT(*)
        FROM tmp_quality_check_source
        WHERE UPPER(borough) = 'UNSPECIFIED'

        UNION ALL

        SELECT 'missing_closed_date_for_closed_requests', COUNT(*)
        FROM tmp_quality_check_source
        WHERE UPPER(status) = 'CLOSED'
          AND closed_date IS NULL

        UNION ALL

        SELECT 'negative_resolution_time', COUNT(*)
        FROM tmp_quality_check_source
        WHERE created_date IS NOT NULL
          AND closed_date IS NOT NULL
          AND closed_date::timestamp < created_date::timestamp

        UNION ALL

        SELECT 'invalid_coordinates', COUNT(*)
        FROM tmp_quality_check_source
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND (
              latitude < 40.0
              OR latitude > 41.0
              OR longitude < -75.0
              OR longitude > -73.0
          )

        UNION ALL

        SELECT 'missing_city', COUNT(*)
        FROM tmp_quality_check_source
        WHERE city IS NULL

    )

    INSERT INTO quality_log (
        run_id,
        rule_code,
        check_name,
        issue_category,
        table_name,
        column_name,
        issue_count,
        severity,
        business_impact,
        recommended_action,
        check_status
    )
    SELECT
        v_run_id,
        rules.rule_code,
        rules.check_name,
        rules.issue_category,
        target_table,
        rules.column_name,
        issues.issue_count,

        CASE
            WHEN issues.issue_count <= rules.low_max_issue_count THEN 'Low'

            WHEN rules.critical_min_issue_count IS NOT NULL
                 AND issues.issue_count >= rules.critical_min_issue_count
                THEN 'Critical'

            WHEN rules.high_min_issue_count IS NOT NULL
                 AND issues.issue_count >= rules.high_min_issue_count
                THEN 'High'

            WHEN rules.medium_min_issue_count IS NOT NULL
                 AND issues.issue_count >= rules.medium_min_issue_count
                THEN 'Medium'

            ELSE 'Medium'
        END,

        rules.business_impact,
        rules.recommended_action,

        CASE
            WHEN issues.issue_count = 0 THEN 'pass'
            ELSE 'fail'
        END

    FROM issue_counts issues
    JOIN quality_rules rules
        ON issues.rule_code = rules.rule_code
    WHERE rules.is_active = TRUE;

    DROP TABLE IF EXISTS tmp_quality_check_source;

    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;


-- Run the checks against both tables.
SELECT run_quality_checks('stg_311_requests') AS staging_run_id;
SELECT run_quality_checks('clean_311_requests') AS clean_run_id;


-- Compare results side by side: staging issue count vs. clean issue count,
-- per rule, using each table's most recent run.
WITH latest_runs AS (
    SELECT
        table_name,
        MAX(checked_at) AS latest_checked_at
    FROM quality_log
    GROUP BY table_name
)
SELECT
    ql.rule_code,
    ql.table_name,
    ql.issue_count,
    ql.severity,
    ql.check_status
FROM quality_log ql
JOIN latest_runs lr
    ON ql.table_name = lr.table_name
   AND ql.checked_at = lr.latest_checked_at
ORDER BY ql.rule_code, ql.table_name;