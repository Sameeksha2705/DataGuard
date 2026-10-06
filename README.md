# DataGuard

**An AI-assisted data reliability pipeline for NYC 311 service request data.**

DataGuard ingests raw public service-request data, runs it through a rule-driven SQL quality engine, and layers an AI reviewer on top that correlates issues across a pipeline run, independently judges severity, and automatically routes each issue to the right outcome: a logged alert, a human-review queue, or (for rules that genuinely qualify) an auto-applied mechanical fix.

The goal isn't just to find bad data. It's to decide, automatically and defensibly, what should happen next.

## Key Results

- **100,000+ real NYC 311 records** processed through a staging to clean to quality-check pipeline
- **10 rule-driven SQL quality checks**, with severity thresholds and business impact stored in a database table, not hardcoded
- **A ZIP-code-based backfill** that resolved 10 of 126 "Unspecified" borough records and reduced missing city values from 5,999 to 0, with the unresolved cases left honestly flagged rather than faked
- **An AI reliability agent** (Claude) that reads every failed check in a run together, proposes a shared root cause, and independently classifies severity and recommended action
- **66.7% agreement rate** between the AI's severity judgment and the deterministic rule engine across 9 assessments, with every disagreement following a consistent, explainable pattern (see the [Build Log](docs/BUILD_LOG.md) for the full breakdown)
- **Automated remediation routing**: AI-flagged issues automatically create entries in `data_quality_alerts` (block/warn) or queue to `proposed_fixes` for human review, no manual triage required
- **55 passing automated tests** covering the cleaning pipeline, the AI context builder, the AI reviewer, and the remediation router, using mocked database and API calls

## Architecture

```
Raw CSV (NYC Open Data)
      |
      v
stg_311_requests        (staging: load_id + loaded_at tagging, UNIQUE constraint)
      |
      v
clean_311_requests       (parsed dates, cleaned ZIP codes, ZIP-based borough/city backfill)
      |
      v
quality_checks.sql       (10 rule-driven checks, run against either layer, results in quality_log)
      |
      v
AI Reviewer (Claude)      (correlates failed checks, independently judges severity/action)
      |
      v
Automated Remediation
  |- block / warn       -> data_quality_alerts (automatic)
  |- human_review       -> proposed_fixes (queued, nothing auto-applied)
  `- auto_fix_candidate -> true auto-apply tier (Low/Medium severity only)
```

## Tech Stack

- **Python**: pandas, psycopg2, pytest, unittest.mock
- **PostgreSQL**: schema design, PL/pgSQL functions, foreign keys, CHECK constraints, native array columns
- **Claude API** (model: `claude-haiku-4-5-20251001`): structured JSON output, validated and retried on malformed responses
- **SQL**: parameterized dynamic queries, CTEs, window-style severity classification

## Project Structure

```text
DataGuard/
|-- data/                          # Raw CSV (gitignored, not committed)
|-- notebooks/                     # Early exploratory analysis (Days 1-5)
|-- reports/                       # Generated CSV reports (missing values, data issues, auto-fix)
|-- docs/
|   `-- BUILD_LOG.md               # Full day-by-day build history, bugs found and fixed
|-- scripts/
|   |-- db_utils.py                 # Centralized PostgreSQL connection handling
|   |-- quality_checker.py          # Cleaning, backfill, and reporting functions
|   |-- load_raw_to_postgres.py     # Loads raw CSV into staging
|   |-- load_clean_to_postgres.py   # Applies cleaning, loads into clean table
|   |-- build_context.py            # Gathers a run's failed checks for the AI
|   |-- ai_reviewer.py              # Sends context to Claude, validates, saves results
|   |-- apply_remediation.py        # Routes AI assessments to alerts or human review
|   `-- generate_synthetic_runs.py  # Synthetic scenarios for AI stress-testing
|-- sql/
|   |-- create_tables.sql           # Core schema
|   |-- quality_rules.sql           # Rule definitions and severity thresholds
|   |-- quality_checks.sql          # Parameterized quality-check function
|   |-- ai_tables.sql                # AI layer tables
|   |-- proposed_fixes_table.sql     # Human-review queue table
|   |-- business_queries.sql         # Analytical queries, staging vs. clean comparisons
|   |-- verify_raw_load.sql / verify_quality_log.sql / verify_ai_layer.sql
|   `-- migrations/
|-- tests/                          # 55 tests across the full pipeline
|-- .env.example
`-- .gitignore
```

## Setup & Usage

### Prerequisites

- Python 3.13+ with `pip`
- PostgreSQL, with a database named `dataguard` created
- pgAdmin 4 (or another PostgreSQL client)
- An Anthropic API key (for the AI reviewer layer)

### 1. Install dependencies

```
pip install pandas psycopg2-binary anthropic pytest
```

### 2. Configure credentials

Copy `.env.example` to `.env`, or set these as environment variables:

- `DATAGUARD_DB_HOST`, `DATAGUARD_DB_PORT`, `DATAGUARD_DB_NAME`, `DATAGUARD_DB_USER` (defaults provided; password prompts securely if not set)
- `DATAGUARD_ANTHROPIC_API_KEY` (required for the AI reviewer)

### 3. Build the database schema

In pgAdmin's Query Tool, run in order:

```
sql/create_tables.sql
sql/quality_rules.sql
sql/ai_tables.sql
sql/proposed_fixes_table.sql
```

### 4. Run the pipeline

```
cd scripts
python quality_checker.py            # Generates local reports
python load_raw_to_postgres.py       # Loads raw data into staging
python load_clean_to_postgres.py     # Applies cleaning, loads into clean table
```

Then, in pgAdmin, run `sql/quality_checks.sql` to execute the quality checks against both tables.

### 5. Run the AI reviewer

```
python build_context.py              # Inspect what context would be sent (optional)
python ai_reviewer.py                # Sends context to Claude, saves assessment
python apply_remediation.py          # Routes the assessment to alerts or review
```

### 6. Verify results

Run `sql/verify_raw_load.sql`, `sql/verify_quality_log.sql`, and `sql/verify_ai_layer.sql` in pgAdmin.

## Testing

```
pytest tests/ -v
```

55 tests, all using mocked database cursors and a mocked Claude client, so the suite runs in a few seconds with no live database or API dependency.

## Known Limitations & Honest Scope

- The ZIP-based borough backfill cannot resolve records missing both a borough and a usable ZIP code. A coordinate-based (point-in-polygon) fallback was scoped but deliberately deferred as a stretch goal, not included in this pass.
- The AI's 66.7% agreement rate is drawn from 1 real pipeline run plus 4 deliberately varied synthetic scenarios (clearly labeled `synthetic_test_data` in the database), used to stress-test the mechanism beyond what one real run could show. It is not a claim of statistically meaningful calibration, which would require many real runs accumulated over real time.
- The true mechanical auto-apply tier is currently empty by design: none of DataGuard's 10 quality rules represent a fix that's safe to apply without human judgment. The infrastructure exists for a rule that would genuinely qualify.

See [docs/BUILD_LOG.md](docs/BUILD_LOG.md) for the complete day-by-day build history, including every bug found and how it was diagnosed and fixed.