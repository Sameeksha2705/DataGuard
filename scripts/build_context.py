"""
DataGuard Build Context

Gathers the failed quality checks from a specific pipeline run (or the
most recent run, if none is specified), along with a few sample affected
records per rule, and packages the result as a JSON-serializable
dictionary ready to hand to the AI reviewer.

Can be run standalone to inspect what context would be sent to the AI:
    python build_context.py
    python build_context.py --table stg_311_requests
    python build_context.py --run-id 1aaccaee-ae1d-4cd1-9e3f-d8feb31b23ab
"""

import argparse
import json
from datetime import date, datetime

from db_utils import get_postgres_connection


# Each rule's failing condition, mirrored from quality_checks.sql, used
# to pull a handful of concrete example records for the AI to look at.
# Kept as a small, explicit mapping (rather than derived dynamically)
# since there are only 10 known rules and the conditions are fixed.
RULE_SAMPLE_CONDITIONS = {
    "missing_unique_key": "unique_key IS NULL",
    "duplicate_unique_key": """
        unique_key IN (
            SELECT unique_key FROM {table}
            WHERE unique_key IS NOT NULL
            GROUP BY unique_key
            HAVING COUNT(*) > 1
        )
    """,
    "missing_created_date": "created_date IS NULL",
    "missing_complaint_type": "complaint_type IS NULL",
    "missing_borough": "borough IS NULL",
    "unspecified_borough": "UPPER(borough) = 'UNSPECIFIED'",
    "missing_closed_date_for_closed_requests": "UPPER(status) = 'CLOSED' AND closed_date IS NULL",
    "negative_resolution_time": """
        created_date IS NOT NULL
        AND closed_date IS NOT NULL
        AND closed_date::timestamp < created_date::timestamp
    """,
    "invalid_coordinates": """
        latitude IS NOT NULL AND longitude IS NOT NULL
        AND (latitude < 40.0 OR latitude > 41.0 OR longitude < -75.0 OR longitude > -73.0)
    """,
    "missing_city": "city IS NULL",
}

SAMPLE_SIZE = 3


def table_exists(cursor, table_name):
    """
    Checks whether a table actually exists in the database. Used so
    that a non-real table name (e.g. synthetic test data, which has no
    backing table) results in an empty sample list rather than a
    database error -- and, importantly, is checked once up front rather
    than discovered mid-loop, since a failed query would otherwise leave
    the transaction in an aborted state for every subsequent query on
    the same connection.
    """
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        );
        """,
        (table_name,),
    )
    return cursor.fetchone()[0]


def get_latest_run_id(cursor, table_name):
    """
    Returns the run_id of the most recent quality check run for the
    given table, or None if no runs exist for that table.
    """
    cursor.execute(
        """
        SELECT run_id
        FROM quality_log
        WHERE table_name = %s
        ORDER BY checked_at DESC
        LIMIT 1;
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def fetch_failed_checks(cursor, run_id):
    """
    Returns every failed quality_log row for the given run_id, as a
    list of dicts.
    """
    cursor.execute(
        """
        SELECT
            rule_code,
            check_name,
            issue_category,
            table_name,
            column_name,
            issue_count,
            severity,
            business_impact,
            recommended_action
        FROM quality_log
        WHERE run_id = %s
          AND check_status = 'fail'
        ORDER BY issue_count DESC;
        """,
        (run_id,),
    )
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_sample_unique_keys(cursor, table_name, rule_code):
    """
    Returns up to SAMPLE_SIZE unique_key values for records that
    currently fail the given rule_code's condition, or an empty list
    if the rule_code isn't recognized or no matching records exist.

    Caller is responsible for confirming table_name actually exists
    before calling this (see table_exists) -- this function assumes
    it does.
    """
    condition_template = RULE_SAMPLE_CONDITIONS.get(rule_code)
    if condition_template is None:
        return []

    condition = condition_template.format(table=table_name)

    query = f"""
        SELECT unique_key
        FROM {table_name}
        WHERE {condition}
        LIMIT %s;
    """

    cursor.execute(query, (SAMPLE_SIZE,))
    return [row[0] for row in cursor.fetchall()]


def build_run_context(run_id=None, table_name="clean_311_requests"):
    """
    Builds the full context dictionary for a quality check run: the
    run's failed checks, each with a handful of sample affected
    unique_key values.

    If run_id is not provided, uses the most recent run for table_name.

    If table_name does not correspond to a real table (e.g. synthetic
    test data), sample_unique_keys is an empty list for every check
    rather than raising an error.
    """
    connection = None

    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            if run_id is None:
                run_id = get_latest_run_id(cursor, table_name)
                if run_id is None:
                    raise ValueError(
                        f"No quality check runs found for table '{table_name}'."
                    )

            failed_checks = fetch_failed_checks(cursor, run_id)

            table_is_real = table_exists(cursor, table_name)

            for check in failed_checks:
                if table_is_real:
                    check["sample_unique_keys"] = fetch_sample_unique_keys(
                        cursor, table_name, check["rule_code"]
                    )
                else:
                    check["sample_unique_keys"] = []

        return {
            "run_id": str(run_id),
            "table_name": table_name,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        }

    finally:
        if connection:
            connection.close()


def _json_default(value):
    """Handles non-JSON-serializable types (e.g. date/datetime) when printing."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def main():
    """Builds context for a run and prints it as formatted JSON, for inspection."""
    parser = argparse.ArgumentParser(description="Build AI review context for a quality check run.")
    parser.add_argument("--table", default="clean_311_requests", help="Table to build context for.")
    parser.add_argument("--run-id", default=None, help="Specific run_id to use (defaults to most recent).")
    args = parser.parse_args()

    context = build_run_context(run_id=args.run_id, table_name=args.table)
    print(json.dumps(context, indent=2, default=_json_default))


if __name__ == "__main__":
    main()