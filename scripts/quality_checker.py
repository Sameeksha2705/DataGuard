"""
DataGuard Quality Checker

This script contains reusable functions for checking and cleaning
data quality issues in the NYC 311 dataset.

It refactors logic developed in the Day 3, Day 4, and Day 5 notebooks.
"""

import pandas as pd
from pathlib import Path


def load_dataset(file_path):
    """
    Loads a CSV dataset from the given file path.
    """
    return pd.read_csv(file_path)


def create_output_folders(project_root):
    """
    Creates required output folders if they do not already exist.
    """
    data_folder = project_root / "data"
    reports_folder = project_root / "reports"

    data_folder.mkdir(exist_ok=True)
    reports_folder.mkdir(exist_ok=True)

    return data_folder, reports_folder

def classify_missing_severity(missing_percentage):
    """
    Classifies missing value severity based on missing percentage.
    """
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


def create_missing_value_report(dataframe):
    """
    Creates a missing value report for all columns in a DataFrame.
    """
    missing_counts = dataframe.isnull().sum()
    missing_percentages = (missing_counts / len(dataframe)) * 100
    non_null_counts = dataframe.notnull().sum()

    missing_report = pd.DataFrame({
        "column_name": dataframe.columns,
        "data_type": dataframe.dtypes.values,
        "missing_count": missing_counts.values,
        "missing_percentage": missing_percentages.values,
        "non_null_count": non_null_counts.values
    })

    missing_report["missing_severity"] = missing_report["missing_percentage"].apply(
        classify_missing_severity
    )

    missing_report = missing_report.sort_values(
        by="missing_percentage",
        ascending=False
    )

    return missing_report

def check_full_duplicates(dataframe):
    """
    Counts full-row duplicate records in a DataFrame.
    """
    return dataframe.duplicated().sum()


def check_duplicate_keys(dataframe, key_column):
    """
    Counts duplicate values in a key column.
    """
    return dataframe[key_column].duplicated().sum()

def standardize_text_column(series):
    """
    Removes leading/trailing spaces and converts text to uppercase.
    Missing values are preserved.
    """
    return (
        series
        .astype("string")
        .str.strip()
        .str.upper()
    )


def parse_date_columns(dataframe, date_columns):
    """
    Converts selected columns to datetime format.
    Invalid date values are converted to NaT.
    """
    dataframe = dataframe.copy()

    for column in date_columns:
        dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")

    return dataframe


def clean_zip_code(value):
    """
    Converts ZIP code values from float format to clean string format.
    Missing values are preserved.
    """
    if pd.isna(value):
        return pd.NA

    return str(int(value))

def remove_full_duplicates(dataframe):
    """
    Removes full-row duplicate records from a DataFrame.
    """
    return dataframe.drop_duplicates()


def remove_duplicate_keys(dataframe, key_column):
    """
    Removes duplicate records based on a key column.
    Keeps the first occurrence.
    """
    return dataframe.drop_duplicates(subset=[key_column], keep="first")


def create_resolution_time(dataframe, start_column, end_column):
    """
    Creates a resolution_time column by subtracting the start date from the end date.
    """
    dataframe = dataframe.copy()
    dataframe["resolution_time"] = dataframe[end_column] - dataframe[start_column]

    return dataframe

def create_data_issues_report(dataframe):
    """
    Creates a structured data issues report for common data quality problems.
    """
    issues = []

    # Check full-row duplicates
    full_duplicate_count = check_full_duplicates(dataframe)

    issues.append({
        "issue_category": "Duplicates",
        "issue_name": "Full-row duplicate records",
        "column_name": "All columns",
        "issue_count": full_duplicate_count,
        "severity": "Low" if full_duplicate_count == 0 else "High",
        "description": "Records that are completely duplicated across all columns.",
        "recommended_action": "Remove full-row duplicates if found."
    })

    # Check duplicate unique_key values
    if "unique_key" in dataframe.columns:
        duplicate_key_count = check_duplicate_keys(dataframe, "unique_key")

        issues.append({
            "issue_category": "Duplicates",
            "issue_name": "Duplicate unique_key values",
            "column_name": "unique_key",
            "issue_count": duplicate_key_count,
            "severity": "Low" if duplicate_key_count == 0 else "Critical",
            "description": "The unique_key column should uniquely identify each service request.",
            "recommended_action": "Investigate duplicate keys before removing records."
        })

    # Check date columns loaded as object/text
    date_columns = [
        "created_date",
        "closed_date",
        "due_date",
        "resolution_action_updated_date"
    ]

    date_columns_present = [
        column for column in date_columns if column in dataframe.columns
    ]

    object_date_columns = [
        column for column in date_columns_present
        if dataframe[column].dtype == "object"
    ]

    issues.append({
        "issue_category": "Data Types",
        "issue_name": "Date columns loaded as object/text",
        "column_name": ", ".join(object_date_columns),
        "issue_count": len(object_date_columns),
        "severity": "Medium" if len(object_date_columns) > 0 else "Low",
        "description": "Date columns should be converted to datetime format for time-based analysis.",
        "recommended_action": "Convert date columns using pd.to_datetime(errors='coerce')."
    })

    # Check incident_zip data type
    if "incident_zip" in dataframe.columns:
        zip_is_float = dataframe["incident_zip"].dtype == "float64"

        issues.append({
            "issue_category": "Data Types",
            "issue_name": "incident_zip loaded as float",
            "column_name": "incident_zip",
            "issue_count": int(zip_is_float),
            "severity": "Medium" if zip_is_float else "Low",
            "description": "ZIP codes are identifiers, not numeric measurements.",
            "recommended_action": "Create a cleaned ZIP code string column."
        })

    # Check unspecified borough values
    if "borough" in dataframe.columns:
        borough_clean = dataframe["borough"].astype("string").str.strip().str.upper()
        unspecified_borough_count = (borough_clean == "UNSPECIFIED").sum()

        issues.append({
            "issue_category": "Formatting",
            "issue_name": "Unspecified borough values",
            "column_name": "borough",
            "issue_count": unspecified_borough_count,
            "severity": "Medium" if unspecified_borough_count > 0 else "Low",
            "description": "Some records do not have a specific borough assigned.",
            "recommended_action": "Review unspecified borough records before geographic analysis."
        })

    # Check unexpected status values
    if "status" in dataframe.columns:
        expected_status_values = {
            "CLOSED",
            "OPEN",
            "IN PROGRESS",
            "STARTED",
            "ASSIGNED",
            "PENDING"
        }

        status_clean = dataframe["status"].astype("string").str.strip().str.upper()
        unexpected_status_count = (~status_clean.isin(expected_status_values)).sum()

        issues.append({
            "issue_category": "Formatting",
            "issue_name": "Unexpected status values",
            "column_name": "status",
            "issue_count": unexpected_status_count,
            "severity": "Medium" if unexpected_status_count > 0 else "Low",
            "description": "Status values should match the expected set of request statuses.",
            "recommended_action": "Review unexpected status values if found."
        })

    # Check city missing values
    if "city" in dataframe.columns:
        city_missing_count = dataframe["city"].isnull().sum()

        issues.append({
            "issue_category": "Formatting / Consistency",
            "issue_name": "Missing city values",
            "column_name": "city",
            "issue_count": city_missing_count,
            "severity": "Medium" if city_missing_count > 0 else "Low",
            "description": "The city column has missing values and may contain mixed geographic levels.",
            "recommended_action": "Review city values before city-level reporting."
        })

    # Check negative resolution time
    if "created_date" in dataframe.columns and "closed_date" in dataframe.columns:
        temp_df = dataframe.copy()
        temp_df = parse_date_columns(temp_df, ["created_date", "closed_date"])
        temp_df = create_resolution_time(temp_df, "created_date", "closed_date")

        negative_resolution_count = (
            temp_df["resolution_time"] < pd.Timedelta(0)
        ).sum()

        issues.append({
            "issue_category": "Suspicious Values",
            "issue_name": "Negative resolution time",
            "column_name": "created_date, closed_date",
            "issue_count": negative_resolution_count,
            "severity": "High" if negative_resolution_count > 0 else "Low",
            "description": "Some records have closed_date earlier than created_date.",
            "recommended_action": "Flag these records for review before resolution-time analysis."
        })

    # Check coordinates outside broad NYC-area range
    if "latitude" in dataframe.columns and "longitude" in dataframe.columns:
        invalid_coordinate_count = dataframe[
            (
                dataframe["latitude"].notnull()
            )
            &
            (
                dataframe["longitude"].notnull()
            )
            &
            (
                (dataframe["latitude"] < 40.0)
                |
                (dataframe["latitude"] > 41.0)
                |
                (dataframe["longitude"] < -75.0)
                |
                (dataframe["longitude"] > -73.0)
            )
        ].shape[0]

        issues.append({
            "issue_category": "Suspicious Values",
            "issue_name": "Coordinates outside broad NYC-area range",
            "column_name": "latitude, longitude",
            "issue_count": invalid_coordinate_count,
            "severity": "High" if invalid_coordinate_count > 0 else "Low",
            "description": "Latitude and longitude should fall within a broad NYC-area range.",
            "recommended_action": "Review invalid coordinates if found."
        })

    issues_report = pd.DataFrame(issues)

    return issues_report

def apply_basic_cleaning(dataframe):
    """
    Applies basic safe cleaning steps to a DataFrame and returns
    the cleaned DataFrame and an auto-fix report.
    """
    df_clean = dataframe.copy()
    fixes_applied = []

    text_columns = [
        "borough",
        "city",
        "status",
        "agency",
        "complaint_type",
        "descriptor"
    ]

    text_columns_present = [
        column for column in text_columns if column in df_clean.columns
    ]

    for column in text_columns_present:
        df_clean[column] = standardize_text_column(df_clean[column])

    fixes_applied.append({
        "fix_name": "Standardize text columns",
        "columns_affected": ", ".join(text_columns_present),
        "issue_fixed": "Inconsistent capitalization or extra spaces in text fields",
        "fix_applied": "str.strip() and str.upper()",
        "safe_auto_fix": "Yes",
        "notes": "Text values were standardized while preserving missing values."
    })

    date_columns = [
        "created_date",
        "closed_date",
        "due_date",
        "resolution_action_updated_date"
    ]

    date_columns_present = [
        column for column in date_columns if column in df_clean.columns
    ]

    df_clean = parse_date_columns(df_clean, date_columns_present)

    fixes_applied.append({
        "fix_name": "Parse date columns",
        "columns_affected": ", ".join(date_columns_present),
        "issue_fixed": "Date columns loaded as object/text",
        "fix_applied": "pd.to_datetime(errors='coerce')",
        "safe_auto_fix": "Yes",
        "notes": "Date columns were converted to datetime format for reliable time-based analysis."
    })

    if "incident_zip" in df_clean.columns:
        df_clean["incident_zip_clean"] = df_clean["incident_zip"].apply(clean_zip_code)

        fixes_applied.append({
            "fix_name": "Clean ZIP code format",
            "columns_affected": "incident_zip",
            "issue_fixed": "ZIP codes loaded as float values",
            "fix_applied": "Converted ZIP codes from float format to clean string format",
            "safe_auto_fix": "Yes",
            "notes": "Created incident_zip_clean while preserving the original incident_zip column."
        })

    rows_before = df_clean.shape[0]
    df_clean = remove_full_duplicates(df_clean)
    rows_after = df_clean.shape[0]

    fixes_applied.append({
        "fix_name": "Remove full-row duplicates",
        "columns_affected": "All columns",
        "issue_fixed": "Fully duplicated records",
        "fix_applied": "drop_duplicates()",
        "safe_auto_fix": "Yes",
        "notes": f"Removed {rows_before - rows_after} full-row duplicate records."
    })

    if "unique_key" in df_clean.columns:
        rows_before = df_clean.shape[0]
        df_clean = remove_duplicate_keys(df_clean, "unique_key")
        rows_after = df_clean.shape[0]

        fixes_applied.append({
            "fix_name": "Remove duplicate unique_key values",
            "columns_affected": "unique_key",
            "issue_fixed": "Duplicate service request identifiers",
            "fix_applied": "drop_duplicates(subset=['unique_key'], keep='first')",
            "safe_auto_fix": "Yes",
            "notes": f"Removed {rows_before - rows_after} duplicate unique_key records."
        })

    if "created_date" in df_clean.columns and "closed_date" in df_clean.columns:
        df_clean = create_resolution_time(df_clean, "created_date", "closed_date")

        fixes_applied.append({
            "fix_name": "Create resolution_time column",
            "columns_affected": "created_date, closed_date",
            "issue_fixed": "Resolution duration not directly available",
            "fix_applied": "closed_date - created_date",
            "safe_auto_fix": "Yes",
            "notes": "Created resolution_time for time-based analysis."
        })

    auto_fix_report = pd.DataFrame(fixes_applied)

    return df_clean, auto_fix_report

def main():
    """
    Runs the DataGuard quality checker workflow.
    """
    project_root = Path(__file__).resolve().parent.parent

    data_folder, reports_folder = create_output_folders(project_root)

    raw_data_path = data_folder / "nyc_311_raw_100k.csv"

    if not raw_data_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_data_path}")

    print("Loading raw dataset...")
    df = load_dataset(raw_data_path)
    print("Raw dataset shape:", df.shape)

    print("Creating missing value report...")
    missing_report = create_missing_value_report(df)

    print("Creating data issues report...")
    data_issues_report = create_data_issues_report(df)

    print("Applying basic cleaning...")
    df_clean, auto_fix_report = apply_basic_cleaning(df)

    cleaned_data_path = data_folder / "nyc_311_cleaned.csv"
    missing_report_path = reports_folder / "missing_value_report.csv"
    data_issues_report_path = reports_folder / "data_issues_report.csv"
    auto_fix_report_path = reports_folder / "auto_fix_report.csv"

    print("Exporting outputs...")
    df_clean.to_csv(cleaned_data_path, index=False)
    missing_report.to_csv(missing_report_path, index=False)
    data_issues_report.to_csv(data_issues_report_path, index=False)
    auto_fix_report.to_csv(auto_fix_report_path, index=False)

    print("DataGuard quality checker completed successfully.")
    print("Cleaned data saved to:", cleaned_data_path)
    print("Missing value report saved to:", missing_report_path)
    print("Data issues report saved to:", data_issues_report_path)
    print("Auto-fix report saved to:", auto_fix_report_path)


if __name__ == "__main__":
    main()