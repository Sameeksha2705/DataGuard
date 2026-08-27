# DataGuard Database Schema Design

## Purpose

The DataGuard database stores raw NYC 311 data, cleaned NYC 311 data, data quality check results, and data quality alerts.

This database will support the DataGuard pipeline by separating raw input data, cleaned analytics-ready data, and quality monitoring outputs.

## Database Name

`dataguard`

## Planned Tables

### 1. raw_311_requests

Stores the original NYC 311 service request data before cleaning.

Purpose:
- Preserve the raw source data
- Allow comparison between raw and cleaned records
- Support auditability

Example columns:
- unique_key
- created_date
- closed_date
- agency
- complaint_type
- descriptor
- status
- borough
- city
- incident_zip
- latitude
- longitude

### 2. clean_311_requests

Stores cleaned NYC 311 service request data after basic DataGuard cleaning.

Purpose:
- Support analytics and reporting
- Store standardized text columns
- Store parsed date columns
- Store cleaned ZIP codes
- Store resolution_time

Example columns:
- unique_key
- created_date
- closed_date
- agency
- complaint_type
- descriptor
- status
- borough
- city
- incident_zip_clean
- latitude
- longitude
- resolution_time

### 3. quality_log

Stores results from data quality checks.

Purpose:
- Track missing values
- Track duplicate checks
- Track data type issues
- Track suspicious values
- Store severity and recommended action

Example columns:
- check_id
- check_name
- issue_category
- column_name
- issue_count
- severity
- check_timestamp
- recommended_action

### 4. data_quality_alerts

Stores high-risk data quality incidents that may affect downstream analytics.

Purpose:
- Track serious quality failures
- Support the future AI Incident Manager
- Identify which analytics should be trusted, warned, or blocked

Example columns:
- alert_id
- alert_name
- severity
- affected_columns
- affected_analytics
- business_impact
- recommended_action
- alert_timestamp

