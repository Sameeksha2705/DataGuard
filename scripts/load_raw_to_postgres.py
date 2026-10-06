"""
Load NYC 311 Raw Data into PostgreSQL

This script loads selected NYC 311 raw columns into the stg_311_requests
staging table.

It uses a replace-load pattern:
1. Read the local raw CSV file.
2. Validate that required columns exist.
3. Clear the existing stg_311_requests table.
4. Load the fresh 100,000 records, tagged with a new load_id for this run.

This makes the script safe to rerun during development:
running it multiple times will still leave the table with 100,000 rows,
not duplicated rows.
"""

import uuid
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from db_utils import get_postgres_connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "nyc_311_raw_100k.csv"

RAW_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "location_type",
    "incident_zip",
    "incident_address",
    "street_name",
    "address_type",
    "city",
    "status",
    "borough",
    "resolution_description",
    "resolution_action_updated_date",
    "latitude",
    "longitude",
]

BATCH_SIZE = 5000


def load_raw_csv(file_path):
    """
    Loads the NYC 311 raw CSV and keeps only the columns used by DataGuard.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {file_path}")

    dataframe = pd.read_csv(file_path)

    missing_columns = [
        column for column in RAW_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"The raw data file is missing required columns: {missing_columns}"
        )

    dataframe = dataframe[RAW_COLUMNS].copy()

    # Convert pandas missing values such as NaN into Python None
    # so PostgreSQL stores them as NULL.
    dataframe = dataframe.astype(object).where(pd.notna(dataframe), None)

    return dataframe


def get_staging_table_count(cursor):
    """
    Returns the number of records currently stored in stg_311_requests.
    """
    cursor.execute("SELECT COUNT(*) FROM stg_311_requests;")
    return cursor.fetchone()[0]


def clear_staging_table(cursor):
    """
    Clears the staging table before loading fresh data.

    RESTART IDENTITY resets the auto-incrementing record_id column.
    """
    cursor.execute("TRUNCATE TABLE stg_311_requests RESTART IDENTITY;")


def insert_staging_records(cursor, dataframe, load_id):
    """
    Inserts NYC 311 records into the staging table, tagging every row
    with the same load_id for this run.
    """
    insert_query = """
        INSERT INTO stg_311_requests (
            unique_key,
            created_date,
            closed_date,
            agency,
            agency_name,
            complaint_type,
            descriptor,
            location_type,
            incident_zip,
            incident_address,
            street_name,
            address_type,
            city,
            status,
            borough,
            resolution_description,
            resolution_action_updated_date,
            latitude,
            longitude,
            load_id
        )
        VALUES %s;
    """

    records = [
        tuple(row) + (load_id,)
        for row in dataframe.to_numpy()
    ]

    execute_values(
        cursor,
        insert_query,
        records,
        page_size=BATCH_SIZE
    )

    return len(records)


def main():
    """
    Runs the staging data loading process.
    """
    connection = None
    load_id = str(uuid.uuid4())

    try:
        dataframe = load_raw_csv(RAW_DATA_PATH)
        print(f"Raw records prepared for loading: {len(dataframe)}")
        print(f"Load ID for this run: {load_id}")

        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            records_before_load = get_staging_table_count(cursor)
            print(f"Records before load: {records_before_load}")

            clear_staging_table(cursor)
            print("Existing staging table records cleared.")

            inserted_records = insert_staging_records(cursor, dataframe, load_id)

            records_after_load = get_staging_table_count(cursor)

        connection.commit()

        print(f"Records inserted: {inserted_records}")
        print(f"Records after load: {records_after_load}")
        print("Staging data load completed successfully.")

    except Exception as error:
        if connection:
            connection.rollback()

        print("Staging data load failed.")
        print(f"Error: {error}")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()