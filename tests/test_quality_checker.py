"""
Tests for scripts/quality_checker.py

Run from the project root with:
    pytest tests/test_quality_checker.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add the scripts folder to the path so we can import quality_checker directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import quality_checker as qc


# ---------------------------------------------------------------------------
# Day 3: Missing value report functions
# ---------------------------------------------------------------------------

def test_classify_missing_severity_buckets():
    assert qc.classify_missing_severity(0) == "No Missing Values"
    assert qc.classify_missing_severity(4.9) == "Low"
    assert qc.classify_missing_severity(24.9) == "Medium"
    assert qc.classify_missing_severity(74.9) == "High"
    assert qc.classify_missing_severity(75) == "Very High"
    assert qc.classify_missing_severity(100) == "Very High"


def test_classify_business_importance():
    assert qc.classify_business_importance("unique_key") == "Critical"
    assert qc.classify_business_importance("closed_date") == "Important"
    assert qc.classify_business_importance("vehicle_type") == "Conditional"
    assert qc.classify_business_importance("some_unknown_column") == "Optional / Review"


def test_generate_missing_value_report_counts_correctly():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 3, 4],
        "complaint_type": ["Noise", None, "Noise", "Parking"],
        "borough": ["BROOKLYN", "QUEENS", None, None],
    })

    report = qc.generate_missing_value_report(dataframe)

    complaint_row = report[report["column_name"] == "complaint_type"].iloc[0]
    borough_row = report[report["column_name"] == "borough"].iloc[0]

    assert complaint_row["missing_count"] == 1
    assert complaint_row["missing_percentage"] == 25.0
    assert borough_row["missing_count"] == 2
    assert borough_row["missing_percentage"] == 50.0


# ---------------------------------------------------------------------------
# Day 4: Data issues report functions
# ---------------------------------------------------------------------------

def test_check_full_duplicates_detects_exact_repeats():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 2],
        "complaint_type": ["Noise", "Parking", "Parking"],
    })
    assert qc.check_full_duplicates(dataframe) == 1


def test_check_full_duplicates_returns_zero_when_none_exist():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 3],
        "complaint_type": ["Noise", "Parking", "Noise"],
    })
    assert qc.check_full_duplicates(dataframe) == 0


def test_check_duplicate_keys():
    dataframe = pd.DataFrame({"unique_key": [1, 2, 2, 3, 3, 3]})
    # drop_duplicates-based duplicated() counts every repeat after the first.
    assert qc.check_duplicate_keys(dataframe) == 3


def test_check_negative_resolution_time_flags_closed_before_created():
    dataframe = pd.DataFrame({
        "created_date": pd.to_datetime(["2026-01-05", "2026-01-01"]),
        "closed_date": pd.to_datetime(["2026-01-01", "2026-01-10"]),
    })
    # Row 0: closed before created -> negative. Row 1: normal, positive.
    assert qc.check_negative_resolution_time(dataframe) == 1


def test_check_invalid_coordinates_flags_out_of_range_points():
    dataframe = pd.DataFrame({
        "latitude": [40.7, 51.5, None],
        "longitude": [-73.9, -0.1, -73.9],
    })
    # Row 0: valid NYC-area point. Row 1: London coordinates, invalid.
    # Row 2: missing latitude, excluded from the check.
    assert qc.check_invalid_coordinates(dataframe) == 1


# ---------------------------------------------------------------------------
# Day 5: Auto-fix cleaning functions
# ---------------------------------------------------------------------------

def test_standardize_text_column_strips_and_uppercases():
    series = pd.Series([" brooklyn ", "Queens", None])
    result = qc.standardize_text_column(series)
    assert result.iloc[0] == "BROOKLYN"
    assert result.iloc[1] == "QUEENS"
    assert pd.isna(result.iloc[2])


def test_clean_zip_code_converts_float_to_clean_string():
    assert qc.clean_zip_code(11211.0) == "11211"


def test_clean_zip_code_converts_stringified_float_to_clean_string():
    # Covers the case where a value stored in a PostgreSQL TEXT column
    # comes back as a string like '11211.0' rather than a real float.
    assert qc.clean_zip_code("11211.0") == "11211"


def test_clean_zip_code_handles_missing_value():
    assert pd.isna(qc.clean_zip_code(None))
    assert pd.isna(qc.clean_zip_code(float("nan")))


def test_get_borough_from_zip_maps_known_ranges():
    assert qc.get_borough_from_zip("10001") == "MANHATTAN"
    assert qc.get_borough_from_zip("11201") == "BROOKLYN"
    assert qc.get_borough_from_zip("10451") == "BRONX"
    assert qc.get_borough_from_zip("10301") == "STATEN ISLAND"
    assert qc.get_borough_from_zip("11101") == "QUEENS"


def test_get_borough_from_zip_returns_none_for_unknown_or_missing():
    # A ZIP code outside every known NYC range.
    assert qc.get_borough_from_zip("90210") is None
    # Missing value.
    assert qc.get_borough_from_zip(None) is None
    # Unparseable value.
    assert qc.get_borough_from_zip("not-a-zip") is None


def test_backfill_borough_and_city_fills_only_missing_or_unspecified():
    dataframe = pd.DataFrame({
        "incident_zip_clean": ["10001", "11201", "10451"],
        "borough": ["UNSPECIFIED", None, "BRONX"],  # last one already correct
        "city": ["NEW YORK", "BROOKLYN", "BRONX"],
    })

    result = qc.backfill_borough_and_city(dataframe)

    # Row 0: was UNSPECIFIED, should be backfilled from ZIP 10001.
    assert result["borough"].iloc[0] == "MANHATTAN"
    # Row 1: was missing, should be backfilled from ZIP 11201.
    assert result["borough"].iloc[1] == "BROOKLYN"
    # Row 2: already had a real value (BRONX), should NOT be overwritten.
    assert result["borough"].iloc[2] == "BRONX"


def test_backfill_borough_and_city_fills_missing_city_from_borough():
    dataframe = pd.DataFrame({
        "incident_zip_clean": ["10001"],
        "borough": ["UNSPECIFIED"],
        "city": [None],
    })

    result = qc.backfill_borough_and_city(dataframe)

    # Borough backfilled from ZIP first, then city backfilled from that borough.
    assert result["borough"].iloc[0] == "MANHATTAN"
    assert result["city"].iloc[0] == "MANHATTAN"


def test_remove_full_duplicates_removes_exact_repeats():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 2],
        "complaint_type": ["Noise", "Parking", "Parking"],
    })
    result = qc.remove_full_duplicates(dataframe)
    assert len(result) == 2


def test_remove_duplicate_keys_keeps_first_occurrence():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 2],
        "complaint_type": ["Noise", "Parking", "DIFFERENT_VALUE"],
    })
    result = qc.remove_duplicate_keys(dataframe, "unique_key")
    assert len(result) == 2
    assert result[result["unique_key"] == 2]["complaint_type"].iloc[0] == "Parking"


def test_create_resolution_time_computes_correct_duration():
    dataframe = pd.DataFrame({
        "created_date": pd.to_datetime(["2026-01-01"]),
        "closed_date": pd.to_datetime(["2026-01-03"]),
    })
    result = qc.create_resolution_time(dataframe, "created_date", "closed_date")
    assert result["resolution_time"].iloc[0] == pd.Timedelta(days=2)


def test_apply_auto_fixes_runs_end_to_end_without_error():
    dataframe = pd.DataFrame({
        "unique_key": [1, 2, 2],
        "created_date": ["2026-01-01", "2026-01-02", "2026-01-02"],
        "closed_date": ["2026-01-03", "2026-01-05", "2026-01-05"],
        "due_date": [None, None, None],
        "resolution_action_updated_date": [None, None, None],
        "borough": [" brooklyn ", "QUEENS", "QUEENS"],
        "city": ["nyc", "nyc", "nyc"],
        "status": ["closed", "open", "open"],
        "agency": ["nypd", "dot", "dot"],
        "complaint_type": ["noise", "parking", "parking"],
        "descriptor": ["loud", "blocked", "blocked"],
        "incident_zip": [11211.0, 10001.0, 10001.0],
    })

    cleaned_df, auto_fix_report = qc.apply_auto_fixes(dataframe)

    # Duplicate unique_key row should have been removed.
    assert len(cleaned_df) == 2
    # incident_zip_clean should exist and be a clean string.
    assert "incident_zip_clean" in cleaned_df.columns
    assert cleaned_df["incident_zip_clean"].iloc[0] == "11211"
    # resolution_time should exist.
    assert "resolution_time" in cleaned_df.columns
    # The report should describe every fix applied, including the new
    # borough/city backfill step (7 total fixes now, not 6).
    assert len(auto_fix_report) == 7