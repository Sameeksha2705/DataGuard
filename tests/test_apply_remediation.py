"""
Tests for scripts/apply_remediation.py

Uses mocked database cursors, so these tests run instantly without
needing a real database.

Run from the project root with:
    pytest tests/test_apply_remediation.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import apply_remediation as remediation


# ---------------------------------------------------------------------------
# qualifies_for_auto_apply
# ---------------------------------------------------------------------------

def test_qualifies_for_auto_apply_true_for_low_severity_auto_fix():
    assessment = {"ai_action": "auto_fix_candidate", "ai_severity": "Low"}
    assert remediation.qualifies_for_auto_apply(assessment) is True


def test_qualifies_for_auto_apply_true_for_medium_severity_auto_fix():
    assessment = {"ai_action": "auto_fix_candidate", "ai_severity": "Medium"}
    assert remediation.qualifies_for_auto_apply(assessment) is True


def test_qualifies_for_auto_apply_false_for_high_severity_even_if_auto_fix():
    """
    High/Critical severity should never qualify for auto-apply,
    regardless of the recommended action -- this is the extra safety
    margin the design relies on.
    """
    assessment = {"ai_action": "auto_fix_candidate", "ai_severity": "High"}
    assert remediation.qualifies_for_auto_apply(assessment) is False


def test_qualifies_for_auto_apply_false_for_block_action():
    assessment = {"ai_action": "block", "ai_severity": "Low"}
    assert remediation.qualifies_for_auto_apply(assessment) is False


def test_qualifies_for_auto_apply_false_for_human_review_action():
    assessment = {"ai_action": "human_review", "ai_severity": "Medium"}
    assert remediation.qualifies_for_auto_apply(assessment) is False


# ---------------------------------------------------------------------------
# fetch_all_affected_unique_keys
# ---------------------------------------------------------------------------

def test_fetch_all_affected_unique_keys_returns_empty_when_table_not_real():
    mock_cursor = MagicMock()

    result = remediation.fetch_all_affected_unique_keys(
        mock_cursor, "synthetic_test_data", "missing_city", table_is_real=False
    )

    assert result == []
    # Should not even attempt a query against a non-existent table.
    mock_cursor.execute.assert_not_called()


def test_fetch_all_affected_unique_keys_queries_when_table_is_real():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]

    result = remediation.fetch_all_affected_unique_keys(
        mock_cursor, "clean_311_requests", "missing_city", table_is_real=True
    )

    assert result == [1, 2, 3]
    mock_cursor.execute.assert_called_once()


def test_fetch_all_affected_unique_keys_returns_empty_for_unknown_rule():
    mock_cursor = MagicMock()

    result = remediation.fetch_all_affected_unique_keys(
        mock_cursor, "clean_311_requests", "not_a_real_rule", table_is_real=True
    )

    assert result == []


# ---------------------------------------------------------------------------
# get_latest_run_id
# ---------------------------------------------------------------------------

def test_get_latest_run_id_returns_run_id_when_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("some-run-id",)

    result = remediation.get_latest_run_id(mock_cursor, "clean_311_requests")

    assert result == "some-run-id"


def test_get_latest_run_id_returns_none_when_not_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    result = remediation.get_latest_run_id(mock_cursor, "clean_311_requests")

    assert result is None


# ---------------------------------------------------------------------------
# create_alert / insert_proposed_fix (verify the right SQL gets executed)
# ---------------------------------------------------------------------------

def test_create_alert_executes_insert_with_expected_values():
    mock_cursor = MagicMock()
    assessment = {
        "rule_code": "missing_city",
        "ai_action": "block",
        "ai_severity": "Critical",
        "explanation": "Something is badly wrong.",
        "business_metrics_at_risk": ["City-level reporting"],
    }

    remediation.create_alert(mock_cursor, assessment, affected_keys=[1, 2, 3])

    mock_cursor.execute.assert_called_once()
    inserted_values = mock_cursor.execute.call_args[0][1]
    assert inserted_values[0] == "missing_city_block"
    assert inserted_values[1] == "Critical"


def test_insert_proposed_fix_executes_insert_with_pending_status():
    mock_cursor = MagicMock()
    assessment = {
        "rule_code": "invalid_coordinates",
        "ai_action": "human_review",
        "ai_severity": "High",
        "explanation": "Needs a human to decide.",
    }

    remediation.insert_proposed_fix(
        mock_cursor, "some-run-id", assessment, affected_unique_keys=[10, 20]
    )

    mock_cursor.execute.assert_called_once()
    executed_query = mock_cursor.execute.call_args[0][0]
    assert "pending_review" in executed_query