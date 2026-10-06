-- DataGuard AI Layer Verification Queries

-- Overall agreement rate: how often does the AI's severity assessment
-- match the rule engine's severity, across every assessment ever logged.
SELECT
    COUNT(*) AS total_assessments,
    SUM(CASE WHEN agrees_with_rule_engine THEN 1 ELSE 0 END) AS agreements,
    ROUND(
        100.0 * SUM(CASE WHEN agrees_with_rule_engine THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS agreement_percentage
FROM ai_incident_reports;


-- Agreement rate broken down by rule_code, to see if disagreement
-- clusters around specific kinds of issues rather than being spread
-- evenly across all rules.
SELECT
    rule_code,
    COUNT(*) AS total_assessments,
    SUM(CASE WHEN agrees_with_rule_engine THEN 1 ELSE 0 END) AS agreements,
    ROUND(
        100.0 * SUM(CASE WHEN agrees_with_rule_engine THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS agreement_percentage
FROM ai_incident_reports
GROUP BY rule_code
ORDER BY agreement_percentage ASC;


-- The actual disagreement cases, with the AI's stated reason for each --
-- this is the evidence for "where did the AI add judgment beyond the
-- static rule engine," not just a number.
SELECT
    run_id,
    rule_code,
    ai_severity,
    ai_action,
    disagreement_reason,
    explanation
FROM ai_incident_reports
WHERE agrees_with_rule_engine = FALSE
ORDER BY created_at DESC;


-- Distribution of the AI's recommended actions, to see how often it's
-- actually recommending auto-fix vs. human review vs. warn vs. block.
SELECT
    ai_action,
    COUNT(*) AS assessment_count
FROM ai_incident_reports
GROUP BY ai_action
ORDER BY assessment_count DESC;