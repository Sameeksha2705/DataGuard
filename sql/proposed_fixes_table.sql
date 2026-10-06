-- DataGuard Proposed Fixes Table
--
-- Holds remediation actions proposed by the AI reviewer that require a
-- human decision before anything is applied to real data. Every row
-- here starts as 'pending_review' and is never auto-applied -- that is
-- the entire point of this table, as distinct from mechanical fixes
-- that are safe to apply automatically (see the tiered logic in
-- apply_remediation.py).

CREATE TABLE IF NOT EXISTS proposed_fixes (
    fix_id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    rule_code TEXT NOT NULL REFERENCES quality_rules(rule_code),
    ai_severity TEXT NOT NULL,
    ai_action TEXT NOT NULL,
    affected_unique_keys BIGINT[] NOT NULL,
    proposed_change TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_review',
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_status CHECK (
        status IN ('pending_review', 'approved', 'rejected', 'applied')
    )
);