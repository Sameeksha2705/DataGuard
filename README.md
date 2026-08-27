# DataGuard

DataGuard is a 30-day data engineering and analytics project focused on building an automated data quality pipeline with AI-powered business intelligence.

The project uses the NYC 311 service requests dataset as a real-world public dataset. The goal is to move from raw data discovery to data quality checks, cleaning, SQL analysis, pipeline automation, cloud storage, dashboards, and an AI-powered business question-answering layer.

## Current Progress

### Day 1: NYC 311 Data Discovery

Completed:

* Set up a professional project folder structure
* Created the first Jupyter notebook
* Verified the Anaconda Python kernel and pandas setup
* Loaded a 100,000-row sample of the NYC 311 dataset
* Confirmed the dataset contains 100,000 rows and 44 columns
* Created a column inventory with column names and data types
* Previewed the first and last records using `head()` and `tail()`
* Reviewed data types and dataset structure using `dtypes` and `info()`
* Previewed missing values across columns

## Project Structure

```text
DataGuard/
├── data/
│   ├── nyc_311_raw_100k.csv
│   ├── nyc_311_cleaned_day5.csv
│   └── nyc_311_cleaned.csv
├── notebooks/
│   ├── 01_nyc311_data_discovery.ipynb
│   ├── 02_nyc311_basic_business_questions.ipynb
│   ├── 03_nyc311_missing_value_report.ipynb
│   ├── 04_nyc311_data_issues_report.ipynb
│   └── 05_nyc311_auto_fix_functions.ipynb
├── reports/
│   ├── missing_value_report_day3.csv
│   ├── data_issues_report_day4.csv
│   ├── auto_fix_report_day5.csv
│   ├── missing_value_report.csv
│   ├── data_issues_report.csv
│   └── auto_fix_report.csv
├── scripts/
│   ├── quality_checker.py
│   ├── test_db_connection.py
│   └── load_raw_to_postgres.py
├── sql/
│   ├── schema_design.md
│   ├── create_tables.sql
│   └── verify_raw_load.sql
├── .gitignore
└── README.md

## Tools Used So Far

* Python
* pandas
* Jupyter Notebook
* VS Code
* Anaconda
* NYC Open Data

## Next Step

Day 2 will focus on using pandas to answer basic business questions about the NYC 311 dataset, including complaint types, borough-level complaint volume, agency workload, request statuses, and date ranges.

### Day 2: Basic Pandas Business Questions

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

### Day 3: Missing Value Report

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

### Day 4: Data Issues Report

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

### Day 5: Auto-Fix Functions

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

### Day 6: Reusable Quality Checker Script

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

Key result:

The project now has a reusable Python script that can load the raw NYC 311 dataset, generate quality reports, apply basic cleaning, and export cleaned outputs automatically.

### Day 8: PostgreSQL Setup and Database Design

Completed:

- Installed PostgreSQL locally
- Installed pgAdmin 4
- Created the local PostgreSQL database: `dataguard`
- Verified the database using pgAdmin query tool
- Installed `psycopg2-binary` so Python can connect to PostgreSQL
- Created `scripts/test_db_connection.py`
- Successfully connected Python to the `dataguard` database
- Created the `sql` folder
- Created `sql/schema_design.md`
- Planned the core DataGuard database tables:
  - `raw_311_requests`
  - `clean_311_requests`
  - `quality_log`
  - `data_quality_alerts`

Key result:

The DataGuard project now has a working local PostgreSQL database and Python can connect to it successfully.

New files created:

- `scripts/test_db_connection.py`
- `sql/schema_design.md`

### Day 9: PostgreSQL Tables and Raw Data Load

Completed:

- Created `sql/create_tables.sql`
- Created PostgreSQL tables for the DataGuard database:
  - `raw_311_requests`
  - `clean_311_requests`
  - `quality_log`
  - `data_quality_alerts`
- Created `scripts/load_raw_to_postgres.py`
- Loaded 100,000 raw NYC 311 records into the `raw_311_requests` table
- Verified the raw table row count using SQL
- Previewed loaded records using `SELECT * FROM raw_311_requests LIMIT 5`
- Created `sql/verify_raw_load.sql` to store raw-load verification queries

Key result:

The raw NYC 311 dataset is now loaded into PostgreSQL and ready for SQL-based analysis and quality checks.

New files created:

- `sql/create_tables.sql`
- `sql/verify_raw_load.sql`
- `scripts/load_raw_to_postgres.py`