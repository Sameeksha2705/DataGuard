-- Migration 001: Add rule traceability fields to quality_log



ALTER TABLE quality_log

ADD COLUMN IF NOT EXISTS rule_code TEXT;



ALTER TABLE quality_log

ADD COLUMN IF NOT EXISTS business_impact TEXT;