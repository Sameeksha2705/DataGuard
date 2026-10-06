# DataGuard Build Log

Full day-by-day history of how DataGuard was built, including every bug found and how it was diagnosed and fixed. See the main [README](../README.md) for the project overview, architecture, and setup instructions.

## Day 1: NYC 311 Data Discovery

Completed:

- Set up a professional project folder structure
- Created the first Jupyter notebook
- Verified the Anaconda Python kernel and pandas setup
- Loaded a 100,000-row sample of the NYC 311 dataset
- Confirmed the dataset contains 100,000 rows and 44 columns
- Created a column inventory with column names and data types
- Previewed the first and last records using `head()` and `tail()`
- Reviewed data types and dataset structure using `dtypes` and `info()`
- Previewed missing values across columns

## Day 2: Basic Pandas Business Questions

Completed:

- Created the second notebook: `02_nyc311_basic_business_questions.ipynb`
- Loaded the 100,000-row NYC 311 dataset sample
- Practiced selecting individual and multiple columns
- Used `value_counts()` to summarize complaint types, boroughs, agencies, and statuses
- Filtered records for Brooklyn complaints, noise-related complaints, and Brooklyn noise complaints
- Sorted records by `created_date`
- Converted `created_date` and `closed_date` to datetime format
- Answered 10 basic business questions using pandas

Key findings:

- `Illegal Parking` is the most common complaint type in the sample.
- Brooklyn has the highest number of 311 requests.
- NYPD handles the largest number of requests in this sample.
- Most requests are marked as `Closed`.
- The sample covers requests created between June 16, 2026 and June 26, 2026.
- The `city` column may need review later because it contains both borough names and neighborhood/location names.

## Day 3: Missing Value Report

Completed:

- Created the third notebook: `03_nyc311_missing_value_report.ipynb`
- Created a `reports/` folder for exported project reports
- Used `isnull()` to detect missing values
- Calculated missing counts and missing percentages for all columns
- Created a structured missing value report table
- Added percentage-based missing severity classifications
- Added business importance classifications
- Added recommended actions for future handling
- Reviewed critical, important, and conditional fields
- Verified that missing `closed_date` values are associated with non-closed request statuses
- Validated examples of conditional missingness in taxi and bridge/highway fields
- Exported the final report as `reports/missing_value_report_day3.csv`

Key findings:

- 33 out of 44 columns contain at least one missing value.
- 11 columns have no missing values.
- All critical columns have 0 missing values.
- `closed_date` has 25.095% missingness, but the missing values appear expected because those records have non-closed statuses.
- Several highly missing fields are conditional fields that only apply to certain complaint or location types.
- Missing values must be interpreted using business context, not just raw percentages.

## Day 4: Data Issues Report

Completed:

- Created the fourth notebook: `04_nyc311_data_issues_report.ipynb`
- Checked for full-row duplicate records
- Checked for duplicate `unique_key` values
- Reviewed column data types
- Converted date columns to datetime format for quality checks
- Identified date columns that were originally loaded as object/text
- Identified `incident_zip` as a data type/formatting concern because ZIP codes were loaded as floats
- Checked formatting consistency in `borough` and `status`
- Reviewed the `city` column for mixed geographic levels
- Created `resolution_time` using `closed_date - created_date`
- Identified records with negative resolution time
- Checked latitude and longitude ranges for suspicious coordinate values
- Created and exported the Day 4 data issues report as `reports/data_issues_report_day4.csv`

Key findings:

- There are 0 full-row duplicate records.
- There are 0 duplicate `unique_key` values.
- Date-related columns need datetime conversion before reliable time-based analysis.
- `incident_zip` should be treated as an identifier/location code rather than a numeric measurement.
- The `borough` and `status` columns appear mostly standardized.
- The `city` column contains mixed geographic levels, including borough names and neighborhood/location names.
- There are 39 records with negative resolution time, where `closed_date` occurs before `created_date`.
- Available latitude and longitude values fall within a broad NYC-area range.

## Day 5: Auto-Fix Functions

Completed:

- Created the fifth notebook: `05_nyc311_auto_fix_functions.ipynb`
- Preserved the raw dataset as `df`
- Created a cleaned working copy called `df_clean`
- Wrote reusable auto-fix functions for common data quality issues
- Standardized selected text columns using `str.strip()` and `str.upper()`
- Parsed date columns into datetime format
- Created a cleaned ZIP code column called `incident_zip_clean`
- Removed full-row duplicates safely
- Removed duplicate `unique_key` records safely
- Created a `resolution_time` column using `closed_date - created_date`
- Created and exported the Day 5 auto-fix report
- Exported the cleaned dataset as `data/nyc_311_cleaned_day5.csv`

Key findings:

- The raw dataset has 100,000 rows and 44 columns.
- The cleaned dataset has 100,000 rows and 46 columns.
- Two new columns were created: `incident_zip_clean` and `resolution_time`.
- Date columns were successfully converted from object/text format to datetime format.
- ZIP codes were cleaned from float values like `11211.0` into string values like `11211`.
- 0 full-row duplicate records were removed.
- 0 duplicate `unique_key` records were removed.
- 74,905 records have valid `resolution_time`.
- 25,095 records have missing `resolution_time`.
- 39 records still have negative `resolution_time` and should be flagged for review instead of silently fixed.

Outputs created:

- `data/nyc_311_cleaned_day5.csv`
- `reports/auto_fix_report_day5.csv`

## Day 6: Reusable Quality Checker Script

Completed:

- Created the first reusable backend script: `scripts/quality_checker.py`
- Refactored Day 3 missing value logic into reusable functions
- Refactored Day 4 data issue checks into reusable functions
- Refactored Day 5 auto-fix cleaning logic into reusable functions
- Added functions for loading data and creating output folders
- Added duplicate-check functions
- Added missing value severity classification
- Added data issues report generation
- Added basic cleaning workflow
- Added a `main()` function so the script can run end to end
- Successfully ran the script from the terminal
- Generated script-based output files automatically

Script-generated outputs:

- `data/nyc_311_cleaned.csv`
- `reports/missing_value_report.csv`
- `reports/data_issues_report.csv`
- `reports/auto_fix_report.csv`

Key result: the project now has a reusable Python script that can load the raw NYC 311 dataset, generate quality reports, apply basic cleaning, and export cleaned outputs automatically.

## Day 8: PostgreSQL Setup and Database Design

Completed:

- Installed PostgreSQL locally and pgAdmin 4
- Created the local PostgreSQL database: `dataguard`
- Verified the database using pgAdmin query tool
- Installed `psycopg2-binary` so Python can connect to PostgreSQL
- Created `scripts/test_db_connection.py`, successfully connected Python to the `dataguard` database
- Created `sql/schema_design.md`, planning the core tables: `raw_311_requests`, `clean_311_requests`, `quality_log`, `data_quality_alerts`

Key result: the project now has a working local PostgreSQL database and Python can connect to it successfully.

New files: `scripts/test_db_connection.py`, `sql/schema_design.md`

## Day 9: PostgreSQL Tables and Raw Data Load

Completed:

- Created `sql/create_tables.sql`, creating the four core tables
- Created `scripts/load_raw_to_postgres.py`
- Loaded 100,000 raw NYC 311 records into the `raw_311_requests` table
- Verified the raw table row count using SQL
- Created `sql/verify_raw_load.sql` for raw-load verification queries

Key result: the raw NYC 311 dataset is loaded into PostgreSQL and ready for SQL-based analysis and quality checks.

New files: `sql/create_tables.sql`, `sql/verify_raw_load.sql`, `scripts/load_raw_to_postgres.py`

## Day 10: SQL Business Queries

Completed:

- Created `sql/business_queries.sql` with 10 queries using `SELECT`, `COUNT`, `GROUP BY`, `ORDER BY`, `LIMIT`, `WHERE`, `CASE`, and `ILIKE`
- Analyzed top complaint types, borough volume, status distribution, agency workload, city/location volume, descriptors, noise complaints by borough, closed vs. not closed, and top complaint types in Brooklyn

Key result: the project has a SQL business query layer analyzing raw NYC 311 data directly inside PostgreSQL.

New file: `sql/business_queries.sql`

## Day 11: Data Quality Rule Engine and Bug Fix

Completed:

- Created `sql/quality_rules.sql`, defining a `quality_rules` table storing severity thresholds and business impact per rule instead of hardcoding them in the check script
- Populated `quality_rules` with 10 active rules covering completeness, uniqueness, validity, and consistency checks
- **Found and fixed a bug** in `sql/quality_checks.sql` where `rule_code` and `business_impact` were missing from the `INSERT` statement, causing those columns to log as `NULL` in `quality_log` even though the join to `quality_rules` had the correct values available
- Renamed `raw_311_requests` to `stg_311_requests` to reflect that it is a staging table holding 19 selected columns, not the full untouched 44-column source
- Added a `UNIQUE` constraint on `unique_key` in `stg_311_requests`
- Added `load_id` and `loaded_at` columns to `stg_311_requests` for load traceability
- Added `run_id`, `rule_code`, `table_name`, `business_impact`, and `check_status` columns to `quality_log` for run traceability
- Updated `load_raw_to_postgres.py` to generate a new `load_id` for each run and tag every inserted row with it
- Rebuilt `scripts/quality_checker.py` as a proper Python script (it had previously and mistakenly been overwritten with SQL content), refactoring the Day 3, 4, and 5 notebook logic into reusable functions
- Verified the `quality_checks.sql` fix end to end: `rule_code` and `business_impact` now populate correctly for all 10 rules in a single run, sharing one `run_id`

Key result: the rule engine is now genuinely rule-driven end to end, from `quality_rules` through `quality_checks.sql` into `quality_log`, with every load and check run traceable to a specific `load_id` and `run_id`.

New/updated files: `sql/quality_rules.sql`, `sql/quality_checks.sql`, `sql/create_tables.sql`, `sql/business_queries.sql`, `sql/verify_raw_load.sql`, `scripts/load_raw_to_postgres.py`, `scripts/quality_checker.py`, `.env.example`

## Day 12: Clean Layer, ZIP-Based Backfill, and a Parameterized Quality Check Function

Completed:

- Created `scripts/load_clean_to_postgres.py`, which reads staged data from `stg_311_requests`, applies the same cleaning functions used by `quality_checker.py`, and loads the result into `clean_311_requests`
- **Fixed two bugs** surfaced while building this: `parse_date_columns` assumed a `due_date` column that isn't present in the staging table's narrower column set, and `clean_zip_code` failed on ZIP codes returned from PostgreSQL as stringified floats (e.g. `'11211.0'`) rather than real floats
- Added `get_borough_from_zip` and `backfill_borough_and_city` to `quality_checker.py`, using documented USPS ZIP code ranges to fill in missing or "Unspecified" borough values, and using the resulting borough as a fallback for missing city values
- **Found and fixed a regression** in the first version of the backfill: it unconditionally overwrote `borough` with the result of the ZIP lookup, even when that lookup failed and returned nothing, silently turning 126 "Unspecified" (Medium severity) records into 116 genuinely missing (High severity) records. Fixed by only overwriting when the lookup actually succeeds, leaving unresolved records exactly as they were rather than making them look worse
- Rebuilt `sql/quality_checks.sql` as a parameterized PL/pgSQL function, `run_quality_checks(target_table)`, that runs the same set of checks against either `stg_311_requests` or `clean_311_requests`, with the dynamic table name validated against an explicit allow-list and isolated to a single temp-table-creation step
- Made borough/status comparisons case-insensitive in the quality checks, since the cleaning step uppercases text columns and an exact-case comparison would silently stop matching cleaned data
- `quality_log` no longer truncates between runs; each run is tagged with its own `run_id` and `table_name`, building a running history instead of only keeping the most recent run
- Added `sql/business_queries.sql` queries comparing staging vs. clean borough completeness directly, and an average-resolution-time-by-borough query that only makes sense once `resolution_time` exists as a real interval

Key findings:

- The ZIP-based backfill resolved 10 of 126 "Unspecified" borough records (126 -> 116). The remaining 116 could not be resolved by ZIP code alone, most likely because those records are missing a usable ZIP code as well, not just a borough.
- `missing_city` improved from 5,999 to 0, since city is backfilled from the (partially fixed) borough value, and even an unresolved "UNSPECIFIED" borough is a non-null fallback.
- `missing_borough`, `negative_resolution_time`, and `invalid_coordinates` are identical between staging and clean, as expected: the cleaning pipeline fixes formatting and derivable values, not values that are genuinely absent from the source data or require human judgment to correct.

## Day 13: AI Reliability Agent and Automated Remediation Routing

Completed:

- Created `sql/ai_tables.sql`, defining `ai_incident_reports` (per-issue AI severity/action assessments) and `ai_root_cause_findings` (cross-issue correlations), both with a foreign key back to `quality_rules` so an AI assessment can never reference a rule that doesn't exist
- Created `scripts/build_context.py`, which gathers every failed check from a specific (or most recent) quality check run, plus a handful of real affected `unique_key` values per rule, as JSON ready to send to an LLM
- Created `scripts/ai_reviewer.py`, which sends that context to Claude (model: `claude-haiku-4-5-20251001`) with a system prompt instructing it to: correlate failed checks that share a likely root cause, independently classify each issue's severity and recommended action, and flag disagreements with the rule-based severity with a stated reason
- **Found and fixed a real issue** on the first run: Claude's response was wrapped in a markdown code fence (` ```json ... ``` `) despite being told not to, which broke direct JSON parsing. Added a `strip_code_fences` step and debug logging of the raw response shape before parsing, rather than guessing blindly at the failure
- Added response validation (`validate_assessment_shape`) confirming the AI's response covers exactly the expected set of rule_codes, no more and no fewer, before anything is saved
- Created `sql/verify_ai_layer.sql`: an overall and per-rule agreement-rate query comparing the AI's severity judgment against the rule engine's, a query surfacing the actual disagreement cases with stated reasons, and a breakdown of how often each action type is recommended
- Created the `proposed_fixes` table, with a `CHECK` constraint on `status` so the database itself rejects an invalid status value
- Created `scripts/apply_remediation.py` to act on the AI's recommendations. Initial design routed every non-auto-fix assessment into `proposed_fixes` uniformly, regardless of whether the AI said `warn`, `block`, or `human_review`, meaning two of the four possible AI actions never caused any real automated effect. **Redesigned** so that `block` and `warn` now automatically create a row in `data_quality_alerts`, a table defined in the original schema design (Day 8) specifically to "identify which analytics should be trusted, warned, or blocked," but left unpopulated until this point. `human_review` still queues to `proposed_fixes`. `auto_fix_candidate` (Low/Medium severity only) is a true mechanical auto-apply tier, implemented as infrastructure for a rule that would genuinely qualify, none of DataGuard's current 10 rules represent a judgment-free fix, so this tier is expected to be empty, which is the correct and honest outcome given the current rule set, not a gap

Key findings:

- On the first real run (2 failed checks: `unspecified_borough`, `negative_resolution_time`), the AI's severity and action assessments agreed with the rule engine on both. The more interesting and genuinely novel output was the root cause finding: the AI connected both issues to a single plausible shared cause (incomplete upstream validation during ETL), a correlation the rule engine has no mechanism to make, since `quality_checks.sql` evaluates every rule independently.
- Both real assessments (`warn`, `block`) correctly triggered automatic alert creation in `data_quality_alerts`, each including the specific downstream reports and metrics put at risk (e.g. borough-level SLA compliance, response-time percentiles) rather than a generic "data quality issue" message.
- With only 2 assessments logged at this point, the agreement rate was 100%, not yet a meaningful sample (see Day 14).

New files: `sql/ai_tables.sql`, `sql/verify_ai_layer.sql`, `sql/proposed_fixes_table.sql`, `scripts/build_context.py`, `scripts/ai_reviewer.py`, `scripts/apply_remediation.py`

## Day 14: AI Reliability Agent Stress-Test with Synthetic Scenarios

**Important disclosure:** this entry uses synthetic, hand-crafted `quality_log` data (`table_name = 'synthetic_test_data'`), not real pipeline output. It exists to test the AI review mechanism against a wider range of situations than DataGuard's single real pipeline run could provide, and to produce a less trivial agreement-rate sample. It does **not** demonstrate genuine calibration or learning over time, a real version of that would require many real runs accumulated across real days or weeks, which this project has not yet had the chance to produce. The mechanism (comparing AI judgment against the rule engine across multiple runs) is real and verified; the volume and realism of the data behind it is not.

Completed:

- Created `scripts/generate_synthetic_runs.py`, defining 4 scenarios deliberately designed to test different kinds of judgment: a widespread, high-volume failure across two related rules; an isolated single-record anomaly; two genuinely unrelated issues occurring together; and a known issue type (from the one real run) recurring at a different scale
- Severity for each synthetic issue is computed using the exact same threshold logic as `quality_checks.sql`, reading live from `quality_rules`, so synthetic data is classified identically to how real data would be
- **Found and fixed a bug**: `build_context.py` and `apply_remediation.py` would crash when asked to sample affected records from `synthetic_test_data`, since it isn't a real table. Fixed by adding a `table_exists` check, run once per call rather than discovered mid-loop, so a non-existent table results in an empty record list instead of an aborted database transaction
- Ran `ai_reviewer.py` and `apply_remediation.py` against all 4 synthetic scenarios

Key findings:

- Across 5 total runs (1 real, 4 synthetic) and 9 total issue assessments, the AI agreed with the rule engine's severity 6 times and disagreed 3 times, a **66.7% agreement rate** (see `sql/verify_ai_layer.sql`).
- Every disagreement pushed severity **up** relative to the rule engine, and in every case involved a completeness-style issue (missing city, missing borough, unspecified borough) at high volume, the AI appears to weigh "a large share of records affected" more heavily than the rule engine's fixed numeric thresholds do.
- For issues the rule engine already treats as High regardless of count (`invalid_coordinates`, `negative_resolution_time`), the AI agreed even at a trivial scale (2-3 records), reasoning that these are correctness problems rather than volume problems, its explanation focused on what the corrupted data would break downstream, not how many records were affected.
- In the deliberately unrelated-issues scenario (duplicate keys and missing created_date, with no real shared cause), the AI still populated a root cause finding as the schema requires, but with notably weaker, more hedged language than its other findings, including an explicit note that this might just be synthetic test data rather than a real upstream problem. It did not fabricate a confident false narrative, which was the specific behavior this scenario was designed to check for.

New files: `scripts/generate_synthetic_runs.py`

## Day 6 (Testing Pass): Test Coverage for the AI Layer

Completed:

- Added `tests/test_build_context.py` (9 tests), `tests/test_ai_reviewer.py` (14 tests), and `tests/test_apply_remediation.py` (12 tests), covering the context builder, the AI reviewer's parsing/validation logic, and the remediation router's auto-apply safety logic
- Used `unittest.mock` to fake database cursors and the Anthropic client, so tests run in seconds with no live database or API dependency
- Full suite across all four test files (including the original `test_quality_checker.py`): **55 passed**

## Day 7: Version Control and Publication

Completed:

- Verified `.gitignore` correctly excludes `.env`, raw CSV data, and `__pycache__`
- Staged, committed, and pushed all Day 11-14 work (29 files changed) to GitHub
- Verified with `git status` showing a clean working tree, confirming every local file matches what's published