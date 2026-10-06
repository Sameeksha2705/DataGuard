"""
DataGuard AI Reviewer

Sends a quality check run's failed checks (built by build_context.py) to
Claude, asking it to:
1. Correlate failed checks that share a likely root cause.
2. Independently classify each issue's severity and recommended action.
3. Flag where it disagrees with the rule-based severity, and why.

The response must be valid JSON matching a fixed schema. If Claude's
response isn't valid JSON, the call is retried once with a corrective
follow-up message before giving up.

Results are written to ai_incident_reports (per-issue assessments) and
ai_root_cause_findings (cross-issue correlations).

Usage:
    python ai_reviewer.py
    python ai_reviewer.py --table stg_311_requests
    python ai_reviewer.py --run-id <uuid>
"""

import argparse
import json
import os

from anthropic import Anthropic

from build_context import build_run_context
from db_utils import get_postgres_connection


MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2000

SYSTEM_PROMPT = """You are a data reliability analyst reviewing automated data \
quality check results for a NYC 311 service request pipeline.

You will receive a JSON object describing one quality check run: a list of \
failed checks, each with a rule_code, issue_count, the rule-based severity \
already assigned, business_impact, recommended_action, and a few sample \
affected unique_key values.

Your job:
1. Look across ALL the failed checks together, not independently. If \
multiple issues share a pattern (same column, same underlying cause), name \
that as a probable shared root cause.
2. For each individual issue, assign your own severity (Low, Medium, High, \
or Critical) and recommended action (auto_fix_candidate, human_review, \
warn, or block), which may agree or disagree with the rule-based values \
already provided.
3. If you disagree with the rule-based severity, explain why in one \
sentence. If you agree, disagreement_reason should be null.
4. Only recommend auto_fix_candidate for mechanical, low-risk issues \
(formatting, type coercion). Never recommend it for anything touching \
data integrity (duplicates, missing identifiers, invalid values that \
require judgment to correct).
5. List which business metrics or reports each issue puts at risk.

Respond with ONLY valid JSON, no markdown formatting, no code fences, no \
preamble or explanation outside the JSON. Match this schema exactly:

{
  "root_cause_findings": [
    {
      "shared_pattern": string,
      "related_rule_codes": [string],
      "probable_root_cause": string,
      "confidence": "low" | "medium" | "high"
    }
  ],
  "issue_assessments": [
    {
      "rule_code": string,
      "ai_severity": "Low" | "Medium" | "High" | "Critical",
      "ai_action": "auto_fix_candidate" | "human_review" | "warn" | "block",
      "agrees_with_rule_engine": boolean,
      "disagreement_reason": string | null,
      "business_metrics_at_risk": [string],
      "explanation": string
    }
  ]
}

issue_assessments must include exactly one entry for every rule_code in the \
input, no more and no fewer. root_cause_findings may be an empty list if no \
real correlation exists across the issues."""


def get_api_key():
    """Gets the Anthropic API key from an environment variable."""
    api_key = os.getenv("DATAGUARD_ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DATAGUARD_ANTHROPIC_API_KEY is not set. Set it as an environment "
            "variable before running ai_reviewer.py."
        )
    return api_key


def call_claude(client, user_content):
    """
    Makes a single Claude API call and returns the raw text response.

    Prints debug info about the response shape, since an empty or
    unexpectedly-structured response is otherwise hard to diagnose.
    """
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    print(f"[debug] stop_reason: {message.stop_reason}")
    print(f"[debug] number of content blocks: {len(message.content)}")
    for i, block in enumerate(message.content):
        print(f"[debug] block {i} type: {block.type}")

    if not message.content:
        raise ValueError("Claude returned no content blocks at all.")

    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        raise ValueError(
            f"Claude returned content, but no 'text' type block. "
            f"Block types were: {[block.type for block in message.content]}"
        )

    raw_text = "".join(text_blocks)
    print(f"[debug] raw response length: {len(raw_text)} characters")
    print(f"[debug] raw response (first 500 chars):\n{raw_text[:500]}")

    return raw_text


def strip_code_fences(text):
    """
    Removes a leading/trailing markdown code fence (```json ... ``` or
    ``` ... ```) if present, since models occasionally wrap JSON in one
    despite being asked not to.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


def parse_ai_response(raw_text):
    """
    Parses Claude's response as JSON. Strips markdown code fences first,
    in case one is present despite the system prompt asking for none.
    Raises json.JSONDecodeError if it still isn't valid JSON.
    """
    cleaned = strip_code_fences(raw_text)
    return json.loads(cleaned)


def get_ai_assessment(client, context):
    """
    Sends the run context to Claude and returns the parsed JSON response.
    Retries once with a corrective message if the first response isn't
    valid JSON.
    """
    user_content = json.dumps(context)

    raw_response = call_claude(client, user_content)

    try:
        return parse_ai_response(raw_response)
    except json.JSONDecodeError as error:
        print(f"[debug] First response failed to parse as JSON: {error}")
        retry_prompt = (
            f"Your previous response was not valid JSON. Here it was:\n\n"
            f"{raw_response}\n\n"
            f"Respond again with ONLY the valid JSON object, matching the "
            f"schema described earlier. No markdown, no code fences, no "
            f"other text."
        )
        raw_retry = call_claude(client, retry_prompt)
        return parse_ai_response(raw_retry)


def validate_assessment_shape(assessment, expected_rule_codes):
    """
    Checks that the parsed assessment has the expected top-level keys and
    that issue_assessments covers exactly the expected rule_codes. Raises
    ValueError if the shape doesn't match.
    """
    if "issue_assessments" not in assessment or "root_cause_findings" not in assessment:
        raise ValueError("AI response is missing required top-level keys.")

    returned_rule_codes = {item["rule_code"] for item in assessment["issue_assessments"]}
    if returned_rule_codes != set(expected_rule_codes):
        raise ValueError(
            f"AI response covers rule_codes {returned_rule_codes}, "
            f"expected {set(expected_rule_codes)}."
        )


def save_assessment(cursor, run_id, assessment):
    """Writes the AI's findings and per-issue assessments to the database."""
    for finding in assessment["root_cause_findings"]:
        cursor.execute(
            """
            INSERT INTO ai_root_cause_findings (
                run_id, shared_pattern, related_rule_codes,
                probable_root_cause, confidence
            )
            VALUES (%s, %s, %s, %s, %s);
            """,
            (
                run_id,
                finding["shared_pattern"],
                finding["related_rule_codes"],
                finding["probable_root_cause"],
                finding["confidence"],
            ),
        )

    for issue in assessment["issue_assessments"]:
        cursor.execute(
            """
            INSERT INTO ai_incident_reports (
                run_id, rule_code, ai_severity, ai_action,
                agrees_with_rule_engine, disagreement_reason,
                business_metrics_at_risk, explanation
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                run_id,
                issue["rule_code"],
                issue["ai_severity"],
                issue["ai_action"],
                issue["agrees_with_rule_engine"],
                issue["disagreement_reason"],
                issue["business_metrics_at_risk"],
                issue["explanation"],
            ),
        )


def main():
    parser = argparse.ArgumentParser(description="Run the AI reviewer on a quality check run.")
    parser.add_argument("--table", default="clean_311_requests", help="Table to build context for.")
    parser.add_argument("--run-id", default=None, help="Specific run_id to use (defaults to most recent).")
    args = parser.parse_args()

    print("Building context...")
    context = build_run_context(run_id=args.run_id, table_name=args.table)
    print(f"Run ID: {context['run_id']}")
    print(f"Failed checks found: {context['failed_check_count']}")

    if context["failed_check_count"] == 0:
        print("No failed checks for this run. Nothing to review.")
        return

    expected_rule_codes = [check["rule_code"] for check in context["failed_checks"]]

    client = Anthropic(api_key=get_api_key())

    print("Calling Claude...")
    assessment = get_ai_assessment(client, context)

    print("Validating response shape...")
    validate_assessment_shape(assessment, expected_rule_codes)

    print("Saving to database...")
    connection = None
    try:
        connection = get_postgres_connection()
        with connection.cursor() as cursor:
            save_assessment(cursor, context["run_id"], assessment)
        connection.commit()
        print("AI review saved successfully.")
    except Exception as error:
        if connection:
            connection.rollback()
        print("Failed to save AI review.")
        print(f"Error: {error}")
        raise
    finally:
        if connection:
            connection.close()

    print("\n--- AI Assessment Summary ---")
    for issue in assessment["issue_assessments"]:
        agreement = "AGREES" if issue["agrees_with_rule_engine"] else "DISAGREES"
        print(f"{issue['rule_code']}: {issue['ai_severity']} / {issue['ai_action']} ({agreement})")

    if assessment["root_cause_findings"]:
        print("\n--- Root Cause Findings ---")
        for finding in assessment["root_cause_findings"]:
            print(f"- {finding['shared_pattern']} ({finding['confidence']} confidence)")
            print(f"  {finding['probable_root_cause']}")


if __name__ == "__main__":
    main()