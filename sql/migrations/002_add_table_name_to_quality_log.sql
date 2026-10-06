-- Migration 002: Add source table traceability to quality_log

ALTER TABLE quality_log
ADD COLUMN IF NOT EXISTS table_name TEXT;