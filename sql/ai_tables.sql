-- DataGuard AI Layer Tables
--
-- ai_incident_reports stores the AI agent's per-issue severity/action
-- assessment for each rule in a given quality check run, including
-- whether it agreed with the deterministic rule engine and why, when
-- it disagreed.
--
-- ai_root_cause_findings stores cross-issue correlations the AI agent
-- identifies within a single run -- patterns across multiple rule
-- violations that suggest one shared underlying cause, rather than
-- unrelated problems.

CREATE TABLE IF NOT EXISTS ai_incident_reports (
    report_id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    rule_code TEXT NOT NULL REFERENCES quality_rules(rule_code),
    ai_severity TEXT NOT NULL,
    ai_action TEXT NOT NULL,
    agrees_with_rule_engine BOOLEAN NOT NULL,
    disagreement_reason TEXT,
    business_metrics_at_risk TEXT[],
    explanation TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_root_cause_findings (
    finding_id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    shared_pattern TEXT NOT NULL,
    related_rule_codes TEXT[] NOT NULL,
    probable_root_cause TEXT NOT NULL,
    confidence TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);