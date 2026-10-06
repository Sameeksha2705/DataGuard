-- DataGuard Quality Rule Definitions
-- This file stores the severity thresholds and business meaning of each quality rule.

CREATE TABLE IF NOT EXISTS quality_rules (
    rule_code TEXT PRIMARY KEY,
    check_name TEXT NOT NULL,
    issue_category TEXT NOT NULL,
    column_name TEXT,
    low_max_issue_count INTEGER NOT NULL DEFAULT 0,
    medium_min_issue_count INTEGER,
    high_min_issue_count INTEGER,
    critical_min_issue_count INTEGER,
    business_impact TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

TRUNCATE TABLE quality_rules;

INSERT INTO quality_rules (
    rule_code,
    check_name,
    issue_category,
    column_name,
    low_max_issue_count,
    medium_min_issue_count,
    high_min_issue_count,
    critical_min_issue_count,
    business_impact,
    recommended_action
)
VALUES
(
    'missing_unique_key',
    'Missing unique_key values',
    'Completeness',
    'unique_key',
    0,
    NULL,
    NULL,
    1,
    'Each service request needs a unique identifier. Missing IDs make records unreliable for tracking, deduplication, and joins.',
    'Block affected records from downstream tables and investigate source extraction.'
),
(
    'duplicate_unique_key',
    'Duplicate unique_key values',
    'Uniqueness',
    'unique_key',
    0,
    NULL,
    NULL,
    1,
    'Duplicate request IDs can inflate counts and create conflicting versions of the same service request.',
    'Review duplicate keys before loading into clean analytics tables.'
),
(
    'missing_created_date',
    'Missing created_date values',
    'Completeness',
    'created_date',
    0,
    NULL,
    NULL,
    1,
    'Created date is required for time-based reporting, trend analysis, and resolution-time calculations.',
    'Block affected records from time-based reporting until the source value is corrected.'
),
(
    'missing_complaint_type',
    'Missing complaint_type values',
    'Completeness',
    'complaint_type',
    0,
    NULL,
    1,
    NULL,
    'Complaint type is required for category-level analysis and operational reporting.',
    'Flag records for review before using complaint-type dashboards.'
),
(
    'missing_borough',
    'Missing borough values',
    'Completeness',
    'borough',
    0,
    NULL,
    1,
    NULL,
    'Borough is required for reliable geographic reporting across NYC.',
    'Flag records for geographic enrichment or review.'
),
(
    'unspecified_borough',
    'Unspecified borough values',
    'Validity',
    'borough',
    0,
    1,
    NULL,
    NULL,
    'Unspecified borough values weaken borough-level reporting but do not make the full record unusable.',
    'Flag records and monitor the share of unspecified borough values.'
),
(
    'missing_closed_date_for_closed_requests',
    'Missing closed_date for closed requests',
    'Consistency',
    'closed_date',
    0,
    NULL,
    1,
    NULL,
    'Closed requests should have a closed date. Missing closure dates can break resolution-time metrics.',
    'Exclude affected records from resolution-time analysis until corrected.'
),
(
    'negative_resolution_time',
    'Negative resolution time',
    'Validity',
    'created_date, closed_date',
    0,
    NULL,
    1,
    NULL,
    'A request cannot be closed before it was created. These records distort SLA and response-time analysis.',
    'Flag records for source review and exclude from resolution-time calculations.'
),
(
    'invalid_coordinates',
    'Coordinates outside broad NYC-area range',
    'Validity',
    'latitude, longitude',
    0,
    NULL,
    1,
    NULL,
    'Invalid coordinates can break mapping, clustering, and geographic analysis.',
    'Exclude affected records from map-based reporting and investigate source location fields.'
),
(
    'missing_city',
    'Missing city values',
    'Completeness',
    'city',
    0,
    1,
    5000,
    NULL,
    'Missing city values weaken city/neighborhood-level reporting. High volume missingness can make city-level dashboards unreliable.',
    'Monitor missing city volume and use borough-level reporting when city values are unavailable.'
);
