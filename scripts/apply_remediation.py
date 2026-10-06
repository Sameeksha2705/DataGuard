"""
DataGuard Apply Remediation

Reads the AI's per-issue assessments for a quality check run and acts on
each one according to its recommended action:

- block / warn: automatically creates an alert in data_quality_alerts.
  This is a safe, non-destructive automated action -- it doesn't modify
  or guess at any data, it only raises a flag marking which analytics
  should currently be distrusted (block) or treated with caution (warn).
  data_quality_alerts was designed for exactly this purpose back in the
  original schema design, but had never been populated until now.

- human_review: inserted into proposed_fixes with status
  'pending_review'. This means the AI itself isn't confident enough in
  a specific course of action to recommend one automatically.

- auto_fix_candidate (Low/Medium severity only): the true mechanical
  auto-apply tier. No fix is executed in this version, since none of
  DataGuard's current quality rules represent a safe, judgment-free fix
  -- this tier exists as infrastructure for a rule that would genuinely
  qualify, and is expected to be empty given the current rule set.

Usage:
    python apply_remediation.py
    python apply_remediation.py --table stg_311_requests
    python apply_remediation.py --run-id <uuid>
"""

import argparse

from build_context import RULE_SAMPLE_CONDITIONS, table_exists
from db_utils import get_postgres_connection


AUTO_APPLY_SEVERITIES = {"Low", "Medium"}


def get_latest_run_id(cursor, table_name):
    """Returns the most recent run_id with AI assessments for the given table."""
    cursor.execute(
        """
        SELECT air.run_id
        FROM ai_incident_reports air
        JOIN quality_log ql ON air.run_id = ql.run_id
        WHERE ql.table_name = %s
        ORDER BY air.created_at DESC
        LIMIT 1;
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def fetch_assessments(cursor, run_id):
    """Returns every AI assessment logged for the given run_id."""
    cursor.execute(
        """
        SELECT rule_code, ai_severity, ai_action, explanation,
               business_metrics_at_risk
        FROM ai_incident_reports
        WHERE run_id = %s;
        """,
        (run_id,),
    )
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_all_affected_unique_keys(cursor, table_name, rule_code, table_is_real):
    """
    Returns every unique_key currently matching the given rule_code's
    failing condition (not just a sample). Returns an empty list
    immediately if table_name isn't a real table (e.g. synthetic test
    data), without attempting the query.
    """
    if not table_is_real:
        return []

    condition_template = RULE_SAMPLE_CONDITIONS.get(rule_code)
    if condition_template is None:
        return []

    condition = condition_template.format(table=table_name)
    query = f"SELECT unique_key FROM {table_name} WHERE {condition};"

    cursor.execute(query)
    return [row[0] for row in cursor.fetchall()]


def qualifies_for_auto_apply(assessment):
    """
    An assessment only qualifies for true mechanical auto-apply if the
    AI explicitly recommended auto_fix_candidate AND rated the severity
    as Low or Medium. High/Critical severity is never auto-applied
    regardless of the recommended action, as an extra safety margin.
    """
    return (
        assessment["ai_action"] == "auto_fix_candidate"
        and assessment["ai_severity"] in AUTO_APPLY_SEVERITIES
    )


def create_alert(cursor, assessment, affected_keys):
    """
    Automatically creates a row in data_quality_alerts for a block or
    warn recommendation. This is the table originally designed for this
    exact purpose (see sql/schema_design.md) but never populated until
    now.
    """
    alert_name = f"{assessment['rule_code']}_{assessment['ai_action']}"

    cursor.execute(
        """
        INSERT INTO data_quality_alerts (
            alert_name, severity, affected_columns,
            affected_analytics, business_impact, recommended_action
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            alert_name,
            assessment["ai_severity"],
            assessment["rule_code"],
            ", ".join(assessment["business_metrics_at_risk"] or []),
            assessment["explanation"],
            (
                f"Automatically {assessment['ai_action']}ed by the AI "
                f"reviewer. {len(affected_keys)} records affected."
            ),
        ),
    )


def insert_proposed_fix(cursor, run_id, assessment, affected_unique_keys):
    """Inserts one pending-review row into proposed_fixes."""
    cursor.execute(
        """
        INSERT INTO proposed_fixes (
            run_id, rule_code, ai_severity, ai_action,
            affected_unique_keys, proposed_change, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'pending_review');
        """,
        (
            run_id,
            assessment["rule_code"],
            assessment["ai_severity"],
            assessment["ai_action"],
            affected_unique_keys,
            assessment["explanation"],
        ),
    )


def main():
    parser = argparse.ArgumentParser(description="Act on AI assessments for a quality check run.")
    parser.add_argument("--table", default="clean_311_requests", help="Table the run was checked against.")
    parser.add_argument("--run-id", default=None, help="Specific run_id to use (defaults to most recent).")
    args = parser.parse_args()

    connection = None
    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            run_id = args.run_id or get_latest_run_id(cursor, args.table)
            if run_id is None:
                print(f"No AI assessments found for table '{args.table}'.")
                return

            print(f"Run ID: {run_id}")
            assessments = fetch_assessments(cursor, run_id)
            print(f"Assessments found: {len(assessments)}")

            table_is_real = table_exists(cursor, args.table)
            if not table_is_real:
                print(
                    f"Note: '{args.table}' is not a real table (synthetic "
                    f"data). Affected record counts will be 0."
                )

            alert_count = 0
            queued_count = 0
            auto_apply_eligible_count = 0

            for assessment in assessments:
                affected_keys = fetch_all_affected_unique_keys(
                    cursor, args.table, assessment["rule_code"], table_is_real
                )

                if qualifies_for_auto_apply(assessment):
                    print(
                        f"[auto-apply eligible] {assessment['rule_code']} "
                        f"(severity={assessment['ai_severity']}), but no "
                        f"mechanical fix handler is implemented yet for "
                        f"this rule. Not applied."
                    )
                    auto_apply_eligible_count += 1

                elif assessment["ai_action"] in ("block", "warn"):
                    create_alert(cursor, assessment, affected_keys)
                    print(
                        f"[alert created] {assessment['rule_code']} "
                        f"-> {assessment['ai_action']} "
                        f"({len(affected_keys)} affected records)"
                    )
                    alert_count += 1

                else:  # human_review, or any action/severity combo not otherwise handled
                    insert_proposed_fix(cursor, run_id, assessment, affected_keys)
                    print(
                        f"[queued for review] {assessment['rule_code']} "
                        f"(severity={assessment['ai_severity']}, "
                        f"action={assessment['ai_action']}) "
                        f"({len(affected_keys)} affected records)"
                    )
                    queued_count += 1

        connection.commit()

        print("\n--- Summary ---")
        print(f"Alerts created (block/warn): {alert_count}")
        print(f"Queued for human review: {queued_count}")
        print(f"Auto-apply eligible (no handler yet): {auto_apply_eligible_count}")

    except Exception as error:
        if connection:
            connection.rollback()
        print(f"Failed to apply remediation. Error: {error}")
        raise
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()