"""
DataGuard Generate Synthetic Runs

Creates several clearly-labeled synthetic quality_log entries, standing
in for multiple real pipeline runs over time. This exists ONLY to
demonstrate that the AI review and remediation mechanism can process
and compare multiple runs -- it is NOT real pipeline output, and does
NOT represent genuine historical calibration. See the README for the
full disclosure on what this does and does not prove.

Every row created by this script uses table_name = 'synthetic_test_data',
so it can never be confused with or mixed into real stg_311_requests or
clean_311_requests results.

Usage:
    python generate_synthetic_runs.py
"""

import uuid

from db_utils import get_postgres_connection


SYNTHETIC_TABLE_NAME = "synthetic_test_data"

# Each scenario is a named situation with one or more (rule_code,
# issue_count) pairs, designed to exercise a different kind of judgment
# call than DataGuard's one real pipeline run so far.
SCENARIOS = [
    {
        "name": "Widespread ingestion failure",
        "description": (
            "Both location-related rules spike massively in the same run, "
            "simulating an upstream location-data feed failing entirely."
        ),
        "issues": [
            ("missing_city", 85000),
            ("missing_borough", 42000),
        ],
    },
    {
        "name": "Tiny isolated anomaly",
        "description": (
            "A single rule fails, but at a trivial scale (2 records), "
            "testing whether severity judgment accounts for scale rather "
            "than just the rule firing at all."
        ),
        "issues": [
            ("invalid_coordinates", 2),
        ],
    },
    {
        "name": "Unrelated issues coincidence",
        "description": (
            "Two rules fail in the same run with no plausible shared "
            "cause, testing whether the AI correctly avoids inventing a "
            "false correlation between unrelated problems."
        ),
        "issues": [
            ("duplicate_unique_key", 1500),
            ("missing_created_date", 900),
        ],
    },
    {
        "name": "Known issue, different severity",
        "description": (
            "The same two rules from DataGuard's one real run, but at "
            "different scales (worse borough problem, better resolution-"
            "time problem), testing whether judgment shifts appropriately "
            "with scale for an already-seen issue type."
        ),
        "issues": [
            ("unspecified_borough", 8000),
            ("negative_resolution_time", 3),
        ],
    },
]


def get_rule_definition(cursor, rule_code):
    """Fetches a rule's definition and thresholds from quality_rules."""
    cursor.execute(
        """
        SELECT check_name, issue_category, column_name,
               low_max_issue_count, medium_min_issue_count,
               high_min_issue_count, critical_min_issue_count,
               business_impact, recommended_action
        FROM quality_rules
        WHERE rule_code = %s AND is_active = TRUE;
        """,
        (rule_code,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No active rule found for rule_code '{rule_code}'.")

    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def compute_severity(issue_count, rule_definition):
    """
    Mirrors the exact severity logic used in sql/quality_checks.sql, so
    synthetic data is classified the same way real data would be.
    """
    if issue_count <= rule_definition["low_max_issue_count"]:
        return "Low"

    critical_min = rule_definition["critical_min_issue_count"]
    if critical_min is not None and issue_count >= critical_min:
        return "Critical"

    high_min = rule_definition["high_min_issue_count"]
    if high_min is not None and issue_count >= high_min:
        return "High"

    medium_min = rule_definition["medium_min_issue_count"]
    if medium_min is not None and issue_count >= medium_min:
        return "Medium"

    return "Medium"


def insert_synthetic_check(cursor, run_id, rule_code, issue_count, rule_definition):
    """Inserts one synthetic quality_log row."""
    severity = compute_severity(issue_count, rule_definition)
    check_status = "pass" if issue_count == 0 else "fail"

    cursor.execute(
        """
        INSERT INTO quality_log (
            run_id, rule_code, check_name, issue_category, table_name,
            column_name, issue_count, severity, business_impact,
            recommended_action, check_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            run_id,
            rule_code,
            rule_definition["check_name"],
            rule_definition["issue_category"],
            SYNTHETIC_TABLE_NAME,
            rule_definition["column_name"],
            issue_count,
            severity,
            rule_definition["business_impact"],
            rule_definition["recommended_action"],
            check_status,
        ),
    )

    return severity


def main():
    connection = None
    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            for scenario in SCENARIOS:
                run_id = str(uuid.uuid4())
                print(f"\nScenario: {scenario['name']}")
                print(f"  {scenario['description']}")
                print(f"  run_id: {run_id}")

                for rule_code, issue_count in scenario["issues"]:
                    rule_definition = get_rule_definition(cursor, rule_code)
                    severity = insert_synthetic_check(
                        cursor, run_id, rule_code, issue_count, rule_definition
                    )
                    print(
                        f"    {rule_code}: issue_count={issue_count} "
                        f"-> severity={severity}"
                    )

        connection.commit()
        print(
            f"\n{len(SCENARIOS)} synthetic scenarios created, "
            f"table_name='{SYNTHETIC_TABLE_NAME}'."
        )
        print(
            "Run ai_reviewer.py and apply_remediation.py with "
            f"--table {SYNTHETIC_TABLE_NAME} --run-id <run_id> for each "
            "run_id printed above."
        )

    except Exception as error:
        if connection:
            connection.rollback()
        print(f"Failed to generate synthetic runs. Error: {error}")
        raise
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()