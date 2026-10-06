"""
Tests for scripts/build_context.py

These tests use mocked database cursors instead of a real PostgreSQL
connection, so they run instantly and don't depend on the database
being up or containing any particular data.

Run from the project root with:
    pytest tests/test_build_context.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_context as bc


# ---------------------------------------------------------------------------
# table_exists
# ---------------------------------------------------------------------------

def test_table_exists_returns_true_when_table_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (True,)

    result = bc.table_exists(mock_cursor, "clean_311_requests")

    assert result is True
    mock_cursor.execute.assert_called_once()


def test_table_exists_returns_false_when_table_not_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (False,)

    result = bc.table_exists(mock_cursor, "synthetic_test_data")

    assert result is False


# ---------------------------------------------------------------------------
# get_latest_run_id
# ---------------------------------------------------------------------------

def test_get_latest_run_id_returns_run_id_when_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("some-run-id-123",)

    result = bc.get_latest_run_id(mock_cursor, "clean_311_requests")

    assert result == "some-run-id-123"


def test_get_latest_run_id_returns_none_when_no_runs_exist():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    result = bc.get_latest_run_id(mock_cursor, "clean_311_requests")

    assert result is None


# ---------------------------------------------------------------------------
# fetch_failed_checks
# ---------------------------------------------------------------------------

def test_fetch_failed_checks_builds_dicts_from_rows():
    mock_cursor = MagicMock()
    # cursor.description is a list of tuples; only the first item of
    # each (the column name) is used by our code.
    mock_cursor.description = [
        ("rule_code",), ("check_name",), ("issue_category",),
        ("table_name",), ("column_name",), ("issue_count",),
        ("severity",), ("business_impact",), ("recommended_action",),
    ]
    mock_cursor.fetchall.return_value = [
        ("missing_city", "Missing city values", "Completeness",
         "clean_311_requests", "city", 110, "Medium",
         "Weakens city reporting.", "Monitor volume."),
    ]

    result = bc.fetch_failed_checks(mock_cursor, "some-run-id")

    assert len(result) == 1
    assert result[0]["rule_code"] == "missing_city"
    assert result[0]["issue_count"] == 110


def test_fetch_failed_checks_returns_empty_list_when_nothing_failed():
    mock_cursor = MagicMock()
    mock_cursor.description = [("rule_code",)]
    mock_cursor.fetchall.return_value = []

    result = bc.fetch_failed_checks(mock_cursor, "some-run-id")

    assert result == []


# ---------------------------------------------------------------------------
# fetch_sample_unique_keys
# ---------------------------------------------------------------------------

def test_fetch_sample_unique_keys_returns_keys_for_known_rule():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(69486831,), (69486700,)]

    result = bc.fetch_sample_unique_keys(
        mock_cursor, "clean_311_requests", "missing_city"
    )

    assert result == [69486831, 69486700]


def test_fetch_sample_unique_keys_returns_empty_for_unknown_rule_code():
    mock_cursor = MagicMock()

    result = bc.fetch_sample_unique_keys(
        mock_cursor, "clean_311_requests", "not_a_real_rule"
    )

    assert result == []
    # Should never even attempt a query for an unrecognized rule_code.
    mock_cursor.execute.assert_not_called()


def test_fetch_sample_unique_keys_formats_duplicate_key_condition():
    """
    duplicate_unique_key's condition template includes a nested {table}
    placeholder inside a subquery -- confirms it substitutes correctly
    rather than leaving a literal '{table}' in the query string.
    """
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    bc.fetch_sample_unique_keys(mock_cursor, "stg_311_requests", "duplicate_unique_key")

    executed_query = mock_cursor.execute.call_args[0][0]
    assert "{table}" not in executed_query
    assert "stg_311_requests" in executed_query