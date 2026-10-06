"""
DataGuard Quality Checker

Refactors the Day 3 (missing values), Day 4 (data issues), and Day 5
(auto-fix cleaning) notebook logic into reusable functions, and runs
them end to end from the command line.

Running this script will:
1. Load the raw NYC 311 dataset.
2. Generate a missing value report.
3. Generate a data issues report.
4. Apply basic auto-fix cleaning.
5. Export the cleaned dataset and all reports.
"""

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "nyc_311_raw_100k.csv"
DATA_FOLDER = PROJECT_ROOT / "data"
REPORTS_FOLDER = PROJECT_ROOT / "reports"

DATE_COLUMNS = [
    "created_date",
    "closed_date",
    "due_date",
    "resolution_action_updated_date",
]

TEXT_COLUMNS = [
    "borough",
    "city",
    "status",
    "agency",
    "complaint_type",
    "descriptor",
]

CRITICAL_COLUMNS = [
    "unique_key",
    "created_date",
    "agency",
    "agency_name",
    "complaint_type",
    "status",
]

IMPORTANT_COLUMNS = [
    "closed_date",
    "borough",
    "city",
    "incident_zip",
    "latitude",
    "longitude",
    "location",
    "resolution_description",
    "resolution_action_updated_date",
]

CONDITIONAL_COLUMNS = [
    "taxi_company_borough",
    "taxi_pick_up_location",
    "vehicle_type",
    "bridge_highway_name",
    "bridge_highway_direction",
    "road_ramp",
    "bridge_highway_segment",
    "facility_type",
]

# Documented USPS ZIP code ranges for NYC boroughs. Used to backfill
# missing or Unspecified borough/city values from a reliable ZIP code.
#
# Known limitation: Queens ZIP codes are neighborhood-based rather than
# one clean contiguous range, so this mapping is very reliable for
# Manhattan, Brooklyn, the Bronx, and Staten Island, and reliable but
# slightly approximate for Queens (a handful of Queens ZIP codes may
# fall outside the ranges listed here and will not be matched).
ZIP_TO_BOROUGH_RANGES = [
    (10001, 10282, "MANHATTAN"),
    (10301, 10314, "STATEN ISLAND"),
    (10451, 10475, "BRONX"),
    (11004, 11005, "QUEENS"),
    (11101, 11109, "QUEENS"),
    (11201, 11256, "BROOKLYN"),
    (11351, 11697, "QUEENS"),
]


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def create_output_folders():
    """Creates the data and reports folders if they do not already exist."""
    DATA_FOLDER.mkdir(exist_ok=True)
    REPORTS_FOLDER.mkdir(exist_ok=True)


def load_raw_data(file_path=DATA_PATH):
    """Loads the raw NYC 311 dataset from CSV."""
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {file_path}")

    dataframe = pd.read_csv(file_path)
    return dataframe


# ---------------------------------------------------------------------------
# Day 3: Missing value report
# ---------------------------------------------------------------------------

def classify_missing_severity(missing_percentage):
    """Classifies missing-value severity based on percentage buckets."""
    if missing_percentage == 0:
        return "No Missing Values"
    elif missing_percentage < 5:
        return "Low"
    elif missing_percentage < 25:
        return "Medium"
    elif missing_percentage < 75:
        return "High"
    else:
        return "Very High"


def classify_business_importance(column_name):
    """Classifies a column's business importance."""
    if column_name in CRITICAL_COLUMNS:
        return "Critical"
    elif column_name in IMPORTANT_COLUMNS:
        return "Important"
    elif column_name in CONDITIONAL_COLUMNS:
        return "Conditional"
    else:
        return "Optional / Review"


def recommend_missing_action(row):
    """Recommends an action for a missing-value report row."""
    column_name = row["column_name"]
    missing_count = row["missing_count"]
    business_importance = row["business_importance"]

    if missing_count == 0:
        return "No action needed"
    elif business_importance == "Critical":
        return "Flag as critical data quality issue"
    elif business_importance == "Important" and column_name == "closed_date":
        return "Review with status; missing may be expected for open requests"
    elif business_importance == "Important":
        return "Review and consider flagging or filling with UNKNOWN if appropriate"
    elif business_importance == "Conditional":
        return "Likely expected missingness; validate against related complaint types"
    else:
        return "Optional field; review before deciding to drop, fill, or ignore"


def generate_missing_value_report(dataframe):
    """Builds the full missing value report for a dataframe."""
    missing_report = pd.DataFrame({
        "column_name": dataframe.columns,
        "data_type": dataframe.dtypes.values,
        "missing_count": dataframe.isnull().sum().values,
        "missing_percentage": ((dataframe.isnull().sum() / len(dataframe)) * 100).values,
        "non_null_count": dataframe.notnull().sum().values,
    })

    missing_report = missing_report.sort_values(by="missing_percentage", ascending=False)

    missing_report["missing_severity"] = missing_report["missing_percentage"].apply(
        classify_missing_severity
    )
    missing_report["business_importance"] = missing_report["column_name"].apply(
        classify_business_importance
    )
    missing_report["recommended_action"] = missing_report.apply(
        recommend_missing_action, axis=1
    )

    final_report = missing_report[[
        "column_name",
        "data_type",
        "non_null_count",
        "missing_count",
        "missing_percentage",
        "missing_severity",
        "business_importance",
        "recommended_action",
    ]]

    return final_report


# ---------------------------------------------------------------------------
# Day 4: Data issues report
# ---------------------------------------------------------------------------

def check_full_duplicates(dataframe):
    """Counts full-row duplicate records."""
    return dataframe.duplicated().sum()


def check_duplicate_keys(dataframe, key_column="unique_key"):
    """Counts duplicate values in a key column."""
    return dataframe[key_column].duplicated().sum()


def check_negative_resolution_time(dataframe):
    """Counts records where closed_date occurs before created_date."""
    resolution_time = dataframe["closed_date"] - dataframe["created_date"]
    return (resolution_time < pd.Timedelta(0)).sum()


def check_invalid_coordinates(dataframe):
    """Counts records with latitude/longitude outside a broad NYC-area range."""
    invalid_mask = (
        dataframe["latitude"].notnull()
        & dataframe["longitude"].notnull()
        & (
            (dataframe["latitude"] < 40.0)
            | (dataframe["latitude"] > 41.0)
            | (dataframe["longitude"] < -75.0)
            | (dataframe["longitude"] > -73.0)
        )
    )
    return dataframe[invalid_mask].shape[0]


def generate_data_issues_report(dataframe):
    """Builds the Day 4 data issues report."""
    dataframe = dataframe.copy()

    for column in DATE_COLUMNS:
        dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")

    full_duplicate_count = check_full_duplicates(dataframe)
    duplicate_unique_key_count = check_duplicate_keys(dataframe)
    unspecified_borough_count = (dataframe["borough"] == "Unspecified").sum()
    city_missing_count = dataframe["city"].isnull().sum()
    negative_resolution_count = check_negative_resolution_time(dataframe)
    invalid_coordinate_count = check_invalid_coordinates(dataframe)

    issues = [
        {
            "issue_category": "Duplicates",
            "issue_name": "Full-row duplicate records",
            "column_name": "All columns",
            "issue_count": full_duplicate_count,
            "severity": "Low" if full_duplicate_count == 0 else "High",
            "description": "Checks whether any complete rows are repeated exactly.",
            "recommended_action": (
                "No action needed." if full_duplicate_count == 0
                else "Investigate and remove duplicate rows after validation."
            ),
        },
        {
            "issue_category": "Duplicates",
            "issue_name": "Duplicate unique_key values",
            "column_name": "unique_key",
            "issue_count": duplicate_unique_key_count,
            "severity": "Low" if duplicate_unique_key_count == 0 else "Critical",
            "description": "Checks whether the request ID uniquely identifies each 311 service request.",
            "recommended_action": (
                "No action needed." if duplicate_unique_key_count == 0
                else "Investigate duplicate request IDs before cleaning."
            ),
        },
        {
            "issue_category": "Data Types",
            "issue_name": "Date columns loaded as object/text",
            "column_name": ", ".join(DATE_COLUMNS),
            "issue_count": len(DATE_COLUMNS),
            "severity": "Medium",
            "description": "Date-related columns were loaded as object/text and required conversion to datetime for reliable time-based analysis.",
            "recommended_action": "Convert date columns to datetime during the cleaning step using pd.to_datetime(errors='coerce').",
        },
        {
            "issue_category": "Data Types",
            "issue_name": "incident_zip loaded as float",
            "column_name": "incident_zip",
            "issue_count": dataframe["incident_zip"].notnull().sum(),
            "severity": "Medium",
            "description": "incident_zip is stored as float64, causing ZIP codes to appear with decimal formatting even though ZIP codes are identifiers.",
            "recommended_action": "Convert incident_zip to a cleaned string format during the cleaning step.",
        },
        {
            "issue_category": "Formatting",
            "issue_name": "Unspecified borough values",
            "column_name": "borough",
            "issue_count": unspecified_borough_count,
            "severity": "Low" if unspecified_borough_count == 0 else "Medium",
            "description": "Checks for records where borough is labeled as Unspecified instead of a specific NYC borough.",
            "recommended_action": "Review Unspecified borough records during location data quality checks.",
        },
        {
            "issue_category": "Formatting / Consistency",
            "issue_name": "Mixed geographic levels in city field",
            "column_name": "city",
            "issue_count": city_missing_count,
            "severity": "Medium",
            "description": "The city column contains a mix of borough names, city names, neighborhood/location names, and missing values.",
            "recommended_action": "Review city values and decide whether to standardize, map to boroughs, or use borough/ZIP/location fields for geographic analysis.",
        },
        {
            "issue_category": "Suspicious Values",
            "issue_name": "Negative resolution time",
            "column_name": "created_date, closed_date",
            "issue_count": negative_resolution_count,
            "severity": "High" if negative_resolution_count > 0 else "Low",
            "description": "Checks whether closed_date occurs before created_date, creating an invalid negative resolution time.",
            "recommended_action": (
                "Flag these records for review before using resolution-time analysis."
                if negative_resolution_count > 0 else "No action needed."
            ),
        },
        {
            "issue_category": "Suspicious Values",
            "issue_name": "Coordinates outside broad NYC-area range",
            "column_name": "latitude, longitude",
            "issue_count": invalid_coordinate_count,
            "severity": "Low" if invalid_coordinate_count == 0 else "High",
            "description": "Checks whether available latitude/longitude values fall outside a broad expected NYC-area range.",
            "recommended_action": (
                "No action needed for coordinate range." if invalid_coordinate_count == 0
                else "Flag invalid coordinates for location data review."
            ),
        },
    ]

    return pd.DataFrame(issues)


# ---------------------------------------------------------------------------
# Day 5: Auto-fix cleaning functions
# ---------------------------------------------------------------------------

def standardize_text_column(series):
    """Removes leading/trailing spaces and converts text to uppercase."""
    return series.astype("string").str.strip().str.upper()


def parse_date_columns(dataframe, date_columns):
    """Converts selected columns to datetime format.

    Columns not present in the dataframe are skipped, since not every
    caller provides the same set of columns (e.g. the staging table
    stores a subset of the original raw CSV's columns).
    """
    dataframe = dataframe.copy()
    for column in date_columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
    return dataframe


def clean_zip_code(value):
    """Converts ZIP code values from float or stringified-float format
    into clean string format.

    Handles both a genuine float (e.g. 11211.0, as loaded directly from
    the raw CSV) and a numeric string with a decimal point (e.g. '11211.0',
    as returned when reading a TEXT column back out of PostgreSQL).
    """
    if pd.isna(value):
        return pd.NA
    return str(int(float(value)))


def get_borough_from_zip(zip_code_clean):
    """
    Maps a cleaned 5-digit ZIP code string to its NYC borough, using
    documented USPS ZIP code ranges.

    Returns None if the ZIP code is missing, unparseable, or falls
    outside every known range.
    """
    if pd.isna(zip_code_clean):
        return None

    try:
        zip_int = int(zip_code_clean)
    except (ValueError, TypeError):
        return None

    for start, end, borough in ZIP_TO_BOROUGH_RANGES:
        if start <= zip_int <= end:
            return borough

    return None


def backfill_borough_and_city(dataframe):
    """
    Backfills missing or Unspecified borough values using a ZIP-code-to-
    borough lookup, then backfills any still-missing city values using
    the (now backfilled) borough name as a reasonable fallback.

    This never overwrites an existing, specific borough value already
    present -- it only fills in values that are missing or Unspecified.

    Critically, it also never overwrites a value with a failed lookup:
    if the ZIP code doesn't map to any known borough (missing ZIP, or a
    ZIP outside every documented range), the original borough value is
    left exactly as it was, rather than being replaced with a null. An
    earlier version of this function did overwrite unconditionally,
    which quietly turned "Unspecified" (a Medium-severity issue) into an
    outright missing value (a higher-severity issue) for every ZIP code
    that couldn't be mapped -- a regression, not a fix. This version only
    writes a new borough value when the lookup actually succeeded.

    Requires incident_zip_clean to already exist on the dataframe, and
    assumes borough/city have already been uppercased by
    standardize_text_column (so "Unspecified" is compared as
    "UNSPECIFIED").
    """
    dataframe = dataframe.copy()

    inferred_borough = dataframe["incident_zip_clean"].apply(get_borough_from_zip)

    needs_borough_fill = (
        dataframe["borough"].isna() | (dataframe["borough"] == "UNSPECIFIED")
    )
    can_fill_borough = needs_borough_fill & inferred_borough.notna()

    dataframe.loc[can_fill_borough, "borough"] = inferred_borough[can_fill_borough]

    needs_city_fill = dataframe["city"].isna()
    dataframe.loc[needs_city_fill, "city"] = dataframe.loc[needs_city_fill, "borough"]

    return dataframe


def remove_full_duplicates(dataframe):
    """Removes full-row duplicate records."""
    return dataframe.drop_duplicates()


def remove_duplicate_keys(dataframe, key_column):
    """Removes duplicate records based on a key column, keeping the first occurrence."""
    return dataframe.drop_duplicates(subset=[key_column], keep="first")


def create_resolution_time(dataframe, start_column, end_column):
    """Creates a resolution_time column as end_column minus start_column."""
    dataframe = dataframe.copy()
    dataframe["resolution_time"] = dataframe[end_column] - dataframe[start_column]
    return dataframe


def apply_auto_fixes(dataframe):
    """
    Applies the Day 5 auto-fix cleaning steps and returns the cleaned
    dataframe plus a report describing each fix applied.
    """
    df_clean = dataframe.copy()
    fixes_applied = []

    for column in TEXT_COLUMNS:
        df_clean[column] = standardize_text_column(df_clean[column])

    fixes_applied.append({
        "fix_name": "Standardize text columns",
        "columns_affected": ", ".join(TEXT_COLUMNS),
        "issue_fixed": "Inconsistent capitalization or extra spaces in text fields",
        "fix_applied": "str.strip() and str.upper()",
        "safe_auto_fix": "Yes",
        "notes": "Text values were standardized while preserving missing values.",
    })

    df_clean = parse_date_columns(df_clean, DATE_COLUMNS)
    fixes_applied.append({
        "fix_name": "Parse date columns",
        "columns_affected": ", ".join(DATE_COLUMNS),
        "issue_fixed": "Date columns loaded as object/text",
        "fix_applied": "pd.to_datetime(errors='coerce')",
        "safe_auto_fix": "Yes",
        "notes": "Date columns were converted to datetime format for reliable time-based analysis.",
    })

    df_clean["incident_zip_clean"] = df_clean["incident_zip"].apply(clean_zip_code)
    fixes_applied.append({
        "fix_name": "Clean ZIP code format",
        "columns_affected": "incident_zip",
        "issue_fixed": "ZIP codes loaded as float values",
        "fix_applied": "Converted ZIP codes from float format to clean string format",
        "safe_auto_fix": "Yes",
        "notes": "Created incident_zip_clean while preserving the original incident_zip column.",
    })

    borough_missing_before = (
        df_clean["borough"].isna() | (df_clean["borough"] == "UNSPECIFIED")
    ).sum()
    city_missing_before = df_clean["city"].isna().sum()

    df_clean = backfill_borough_and_city(df_clean)

    borough_missing_after = (
        df_clean["borough"].isna() | (df_clean["borough"] == "UNSPECIFIED")
    ).sum()
    city_missing_after = df_clean["city"].isna().sum()

    fixes_applied.append({
        "fix_name": "Backfill borough and city from ZIP code",
        "columns_affected": "borough, city, incident_zip_clean",
        "issue_fixed": "Missing or Unspecified borough values, missing city values",
        "fix_applied": "ZIP-code-to-borough lookup using documented USPS ranges; city backfilled from resulting borough. Only overwrites when the lookup succeeds -- never replaces an unresolved value with a null.",
        "safe_auto_fix": "Yes, with a known limitation",
        "notes": (
            f"Missing/Unspecified borough reduced from {borough_missing_before} to "
            f"{borough_missing_after}. Missing city reduced from {city_missing_before} "
            f"to {city_missing_after}. Queens ZIP codes are neighborhood-based rather "
            "than one contiguous range, so a small number of records may remain "
            "unfilled and stay flagged as Unspecified/missing rather than being "
            "silently marked as resolved."
        ),
    })

    rows_before = df_clean.shape[0]
    df_clean = remove_full_duplicates(df_clean)
    duplicates_removed = rows_before - df_clean.shape[0]
    fixes_applied.append({
        "fix_name": "Remove full-row duplicates",
        "columns_affected": "All columns",
        "issue_fixed": "Fully duplicated records",
        "fix_applied": "drop_duplicates()",
        "safe_auto_fix": "Yes",
        "notes": f"Removed {duplicates_removed} full-row duplicate records.",
    })

    rows_before = df_clean.shape[0]
    df_clean = remove_duplicate_keys(df_clean, "unique_key")
    duplicate_keys_removed = rows_before - df_clean.shape[0]
    fixes_applied.append({
        "fix_name": "Remove duplicate unique_key values",
        "columns_affected": "unique_key",
        "issue_fixed": "Duplicate service request identifiers",
        "fix_applied": "drop_duplicates(subset=['unique_key'], keep='first')",
        "safe_auto_fix": "Yes",
        "notes": f"Removed {duplicate_keys_removed} duplicate unique_key records.",
    })

    df_clean = create_resolution_time(df_clean, "created_date", "closed_date")
    fixes_applied.append({
        "fix_name": "Create resolution_time column",
        "columns_affected": "created_date, closed_date",
        "issue_fixed": "Resolution duration not directly available",
        "fix_applied": "closed_date - created_date",
        "safe_auto_fix": "Yes",
        "notes": "Created resolution_time for time-based analysis. Missing closed_date values result in missing resolution_time.",
    })

    auto_fix_report = pd.DataFrame(fixes_applied)
    return df_clean, auto_fix_report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Runs the full quality-check and cleaning workflow end to end."""
    create_output_folders()

    print("Loading raw dataset...")
    raw_df = load_raw_data()
    print(f"Raw dataset shape: {raw_df.shape}")

    print("\nGenerating missing value report...")
    missing_report = generate_missing_value_report(raw_df)
    missing_report.to_csv(REPORTS_FOLDER / "missing_value_report.csv", index=False)
    print(f"Saved: {REPORTS_FOLDER / 'missing_value_report.csv'}")

    print("\nGenerating data issues report...")
    issues_report = generate_data_issues_report(raw_df)
    issues_report.to_csv(REPORTS_FOLDER / "data_issues_report.csv", index=False)
    print(f"Saved: {REPORTS_FOLDER / 'data_issues_report.csv'}")

    print("\nApplying auto-fix cleaning...")
    cleaned_df, auto_fix_report = apply_auto_fixes(raw_df)
    cleaned_df.to_csv(DATA_FOLDER / "nyc_311_cleaned.csv", index=False)
    auto_fix_report.to_csv(REPORTS_FOLDER / "auto_fix_report.csv", index=False)
    print(f"Saved: {DATA_FOLDER / 'nyc_311_cleaned.csv'}")
    print(f"Saved: {REPORTS_FOLDER / 'auto_fix_report.csv'}")

    print("\nQuality checker run complete.")
    print(f"Cleaned dataset shape: {cleaned_df.shape}")


if __name__ == "__main__":
    main()