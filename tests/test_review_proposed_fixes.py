"""
Tests for scripts/review_proposed_fixes.py

Uses mocked database cursors, so these tests run instantly without
needing a real database.

Run from the project root with:
    pytest tests/test_review_proposed_fixes.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import review_proposed_fixes as rpf


def test_list_pending_fixes_builds_dicts_from_rows():
    mock_cursor = MagicMock()
    mock_cursor.description = [
        ("fix_id",), ("rule_code",), ("ai_severity",), ("ai_action",),
        ("affected_count",), ("proposed_change",), ("created_at",),
    ]
    mock_cursor.fetchall.return_value = [
        (1, "unspecified_borough", "Medium", "human_review", 116, "Flag for review.", "2026-10-06"),
    ]

    result = rpf.list_pending_fixes(mock_cursor)

    assert len(result) == 1
    assert result[0]["fix_id"] == 1
    assert result[0]["affected_count"] == 116


def test_list_pending_fixes_returns_empty_list_when_none_pending():
    mock_cursor = MagicMock()
    mock_cursor.description = [("fix_id",)]
    mock_cursor.fetchall.return_value = []

    result = rpf.list_pending_fixes(mock_cursor)

    assert result == []


def test_update_fix_status_returns_row_when_update_applies():
    mock_cursor = MagicMock()
    mock_cursor.description = [("fix_id",), ("rule_code",), ("status",)]
    mock_cursor.fetchone.return_value = (3, "invalid_coordinates", "approved")

    result = rpf.update_fix_status(mock_cursor, 3, "approved", "Sameeksha")

    assert result == {"fix_id": 3, "rule_code": "invalid_coordinates", "status": "approved"}
    mock_cursor.execute.assert_called_once()
    executed_params = mock_cursor.execute.call_args[0][1]
    assert executed_params == ("approved", "Sameeksha", 3)


def test_update_fix_status_returns_none_when_fix_id_not_pending():
    """
    Covers both a nonexistent fix_id and a fix_id that was already
    reviewed -- in both cases the WHERE clause matches no rows, so
    RETURNING produces nothing, and fetchone() returns None.
    """
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    result = rpf.update_fix_status(mock_cursor, 999, "rejected", "Sameeksha")

    assert result is None


def test_print_pending_fixes_handles_empty_list(capsys):
    rpf.print_pending_fixes([])
    captured = capsys.readouterr()
    assert "No fixes are currently pending review." in captured.out


def test_print_pending_fixes_prints_fix_details(capsys):
    fixes = [{
        "fix_id": 1,
        "rule_code": "unspecified_borough",
        "ai_severity": "Medium",
        "ai_action": "human_review",
        "affected_count": 116,
        "proposed_change": "Flag for review.",
        "created_at": "2026-10-06",
    }]

    rpf.print_pending_fixes(fixes)
    captured = capsys.readouterr()

    assert "fix_id 1" in captured.out
    assert "unspecified_borough" in captured.out
    assert "116" in captured.out