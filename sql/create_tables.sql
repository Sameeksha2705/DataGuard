-- DataGuard PostgreSQL Table Creation Script

-- Drop tables if they already exist.
-- This makes the script safe to rerun during development.

DROP TABLE IF EXISTS data_quality_alerts;
DROP TABLE IF EXISTS quality_log;
DROP TABLE IF EXISTS clean_311_requests;
DROP TABLE IF EXISTS stg_311_requests;


-- 1. Staging table for raw NYC 311 service requests
-- Stores selected fields from the original raw dataset, tagged by load batch.

CREATE TABLE stg_311_requests (
    record_id SERIAL PRIMARY KEY,
    unique_key BIGINT UNIQUE,
    created_date TEXT,
    closed_date TEXT,
    agency TEXT,
    agency_name TEXT,
    complaint_type TEXT,
    descriptor TEXT,
    location_type TEXT,
    incident_zip TEXT,
    incident_address TEXT,
    street_name TEXT,
    address_type TEXT,
    city TEXT,
    status TEXT,
    borough TEXT,
    resolution_description TEXT,
    resolution_action_updated_date TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    load_id UUID NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 2. Clean NYC 311 service requests table
-- Stores cleaned analytics-ready data.

CREATE TABLE clean_311_requests (
    record_id SERIAL PRIMARY KEY,
    unique_key BIGINT,
    created_date TIMESTAMP,
    closed_date TIMESTAMP,
    agency TEXT,
    agency_name TEXT,
    complaint_type TEXT,
    descriptor TEXT,
    city TEXT,
    status TEXT,
    borough TEXT,
    incident_zip_clean TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    resolution_time INTERVAL
);


-- 3. Quality log table
-- Stores data quality check results, tagged by run for traceability.

CREATE TABLE quality_log (
    check_id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    rule_code TEXT,
    check_name TEXT,
    issue_category TEXT,
    table_name TEXT,
    column_name TEXT,
    issue_count INTEGER,
    severity TEXT,
    business_impact TEXT,
    recommended_action TEXT,
    check_status TEXT,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 4. Data quality alerts table
-- Stores serious data quality incidents for the future AI Incident Manager.

CREATE TABLE data_quality_alerts (
    alert_id SERIAL PRIMARY KEY,
    alert_name TEXT,
    severity TEXT,
    affected_columns TEXT,
    affected_analytics TEXT,
    business_impact TEXT,
    recommended_action TEXT,
    alert_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);