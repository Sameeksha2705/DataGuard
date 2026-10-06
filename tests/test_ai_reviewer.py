"""
Tests for scripts/ai_reviewer.py

Uses mocked database cursors and a mocked Anthropic client, so these
tests run instantly without needing a real database or spending real
API credits.

Run from the project root with:
    pytest tests/test_ai_reviewer.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import ai_reviewer as ar


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------

def test_get_api_key_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("DATAGUARD_ANTHROPIC_API_KEY", "fake-key-for-testing")
    assert ar.get_api_key() == "fake-key-for-testing"


def test_get_api_key_raises_when_not_set(monkeypatch):
    monkeypatch.delenv("DATAGUARD_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        ar.get_api_key()


# ---------------------------------------------------------------------------
# strip_code_fences
# ---------------------------------------------------------------------------

def test_strip_code_fences_removes_json_fence():
    fenced = '```json\n{"a": 1}\n```'
    assert ar.strip_code_fences(fenced) == '{"a": 1}'


def test_strip_code_fences_removes_plain_fence():
    fenced = '```\n{"a": 1}\n```'
    assert ar.strip_code_fences(fenced) == '{"a": 1}'


def test_strip_code_fences_leaves_unfenced_text_unchanged():
    plain = '{"a": 1}'
    assert ar.strip_code_fences(plain) == '{"a": 1}'


# ---------------------------------------------------------------------------
# parse_ai_response
# ---------------------------------------------------------------------------

def test_parse_ai_response_parses_fenced_json():
    fenced = '```json\n{"issue_assessments": []}\n```'
    result = ar.parse_ai_response(fenced)
    assert result == {"issue_assessments": []}


def test_parse_ai_response_raises_on_invalid_json():
    import json
    with pytest.raises(json.JSONDecodeError):
        ar.parse_ai_response("this is not json at all")


# ---------------------------------------------------------------------------
# validate_assessment_shape
# ---------------------------------------------------------------------------

def test_validate_assessment_shape_passes_for_matching_rule_codes():
    assessment = {
        "root_cause_findings": [],
        "issue_assessments": [
            {"rule_code": "missing_city"},
            {"rule_code": "unspecified_borough"},
        ],
    }
    # Should not raise.
    ar.validate_assessment_shape(assessment, ["missing_city", "unspecified_borough"])


def test_validate_assessment_shape_raises_when_rule_code_missing():
    assessment = {
        "root_cause_findings": [],
        "issue_assessments": [{"rule_code": "missing_city"}],
    }
    with pytest.raises(ValueError):
        ar.validate_assessment_shape(assessment, ["missing_city", "unspecified_borough"])


def test_validate_assessment_shape_raises_when_extra_rule_code_present():
    assessment = {
        "root_cause_findings": [],
        "issue_assessments": [
            {"rule_code": "missing_city"},
            {"rule_code": "invented_rule_not_asked_for"},
        ],
    }
    with pytest.raises(ValueError):
        ar.validate_assessment_shape(assessment, ["missing_city"])


def test_validate_assessment_shape_raises_when_top_level_key_missing():
    assessment = {"issue_assessments": []}  # missing root_cause_findings
    with pytest.raises(ValueError):
        ar.validate_assessment_shape(assessment, [])


# ---------------------------------------------------------------------------
# call_claude (mocked Anthropic client)
# ---------------------------------------------------------------------------

def _make_mock_message(text, stop_reason="end_turn", block_type="text"):
    """Builds a fake Claude API response object matching the real shape."""
    mock_block = MagicMock()
    mock_block.type = block_type
    mock_block.text = text

    mock_message = MagicMock()
    mock_message.stop_reason = stop_reason
    mock_message.content = [mock_block]
    return mock_message


def test_call_claude_returns_text_from_response():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_message('{"a": 1}')

    result = ar.call_claude(mock_client, "some user content")

    assert result == '{"a": 1}'


def test_call_claude_raises_when_no_content_blocks():
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.stop_reason = "end_turn"
    mock_message.content = []
    mock_client.messages.create.return_value = mock_message

    with pytest.raises(ValueError):
        ar.call_claude(mock_client, "some user content")


def test_call_claude_raises_when_no_text_block_present():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_message(
        "irrelevant", block_type="not_text"
    )

    with pytest.raises(ValueError):
        ar.call_claude(mock_client, "some user content")


# ---------------------------------------------------------------------------
# get_ai_assessment (retry logic)
# ---------------------------------------------------------------------------

def test_get_ai_assessment_succeeds_on_first_attempt():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_message(
        '{"issue_assessments": [], "root_cause_findings": []}'
    )

    result = ar.get_ai_assessment(mock_client, {"some": "context"})

    assert result == {"issue_assessments": [], "root_cause_findings": []}
    assert mock_client.messages.create.call_count == 1


def test_get_ai_assessment_succeeds_after_one_malformed_attempt():
    mock_client = MagicMock()
    # First call returns garbage, second call returns valid JSON.
    mock_client.messages.create.side_effect = [
        _make_mock_message("not valid json"),
        _make_mock_message('{"issue_assessments": [], "root_cause_findings": []}'),
    ]

    result = ar.get_ai_assessment(mock_client, {"some": "context"}, max_attempts=3)

    assert result == {"issue_assessments": [], "root_cause_findings": []}
    assert mock_client.messages.create.call_count == 2


def test_get_ai_assessment_raises_ai_review_failed_after_all_attempts_exhausted():
    """
    Covers the real failure mode that happened during development: the
    first response and the retry both failed to parse. With only one
    retry, this crashed with an unhandled JSONDecodeError. This test
    confirms that after max_attempts is exhausted, a clean
    AIReviewFailed is raised instead of letting the raw JSONDecodeError
    propagate.
    """
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_message("still not valid json")

    with pytest.raises(ar.AIReviewFailed):
        ar.get_ai_assessment(mock_client, {"some": "context"}, max_attempts=3)

    assert mock_client.messages.create.call_count == 3