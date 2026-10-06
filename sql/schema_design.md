# DataGuard Database Schema Design

## Purpose

The DataGuard database stores staged and cleaned NYC 311 data, data quality check results, AI-generated reliability assessments, and the alerts and review queue they produce.

## Database Name

`dataguard`

## Tables

### 1. stg_311_requests

Staging table holding 19 selected columns from the original 44-column raw CSV. Named "staging," not "raw," since it does not preserve every original source column.

Key columns:
- `record_id` (PK), `unique_key` (`UNIQUE`)
- `created_date`, `closed_date` (TEXT, as originally sourced)
- `agency`, `agency_name`, `complaint_type`, `descriptor`, `location_type`
- `incident_zip`, `incident_address`, `street_name`, `address_type`
- `city`, `status`, `borough`
- `resolution_description`, `resolution_action_updated_date`
- `latitude`, `longitude`
- `load_id` (UUID, one per load run), `loaded_at` (TIMESTAMP)

### 2. clean_311_requests

Cleaned, analytics-ready data: parsed timestamps, a cleaned ZIP code, and ZIP-based backfilled borough/city values where the source was missing or "Unspecified."

Key columns:
- `record_id` (PK), `unique_key`
- `created_date`, `closed_date` (TIMESTAMP, parsed)
- `agency`, `agency_name`, `complaint_type`, `descriptor`
- `city`, `status`, `borough` (backfilled where possible)
- `incident_zip_clean`, `latitude`, `longitude`
- `resolution_time` (INTERVAL)

### 3. quality_rules

Stores severity thresholds, business impact, and recommended actions per rule, so this logic lives in data, not hardcoded in check scripts.

Key columns:
- `rule_code` (PK), `check_name`, `issue_category`, `column_name`
- `low_max_issue_count`, `medium_min_issue_count`, `high_min_issue_count`, `critical_min_issue_count`
- `business_impact`, `recommended_action`, `is_active`

### 4. quality_log

Stores results from every quality check run. Does not truncate between runs; each run is tagged so history accumulates.

Key columns:
- `check_id` (PK), `run_id` (UUID, shared by every row in one run)
- `rule_code`, `check_name`, `issue_category`, `table_name`, `column_name`
- `issue_count`, `severity`, `business_impact`, `recommended_action`
- `check_status` (`pass` / `fail`), `checked_at`

### 5. data_quality_alerts

Stores alerts automatically created by the AI layer for `block` and `warn` recommendations, flagging which analytics should currently be distrusted or treated with caution.

Key columns:
- `alert_id` (PK), `alert_name`, `severity`
- `affected_columns`, `affected_analytics`, `business_impact`, `recommended_action`
- `alert_timestamp`

### 6. ai_incident_reports

Stores the AI's per-issue assessment for a quality check run: its own severity/action judgment, whether it agreed with the rule engine, and why when it disagreed.

Key columns:
- `report_id` (PK), `run_id`, `rule_code` (FK to `quality_rules`)
- `ai_severity`, `ai_action`, `agrees_with_rule_engine`, `disagreement_reason`
- `business_metrics_at_risk` (TEXT[]), `explanation`, `created_at`

### 7. ai_root_cause_findings

Stores cross-issue correlations the AI identifies within a single run, patterns across multiple failed rules suggesting a shared underlying cause.

Key columns:
- `finding_id` (PK), `run_id`
- `shared_pattern`, `related_rule_codes` (TEXT[]), `probable_root_cause`, `confidence`
- `created_at`

### 8. proposed_fixes

Holds AI-flagged issues requiring a human decision (`human_review` action) before anything is applied. Rows start as `pending_review` and are never auto-applied.

Key columns:
- `fix_id` (PK), `run_id`, `rule_code` (FK to `quality_rules`)
- `ai_severity`, `ai_action`, `affected_unique_keys` (BIGINT[]), `proposed_change`
- `status` (`pending_review` / `approved` / `rejected` / `applied`, enforced by a CHECK constraint)
- `reviewed_by`, `reviewed_at`, `created_at`

## Data Flow

```
stg_311_requests -> clean_311_requests -> quality_log
                                              |
                                              v
                                    ai_incident_reports
                                    ai_root_cause_findings
                                              |
                              block/warn -----+----- human_review
                                   |                      |
                          data_quality_alerts      proposed_fixes
```