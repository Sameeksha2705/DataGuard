"""
Load Clean NYC 311 Data into PostgreSQL

This script reads staged data from stg_311_requests, applies the same
auto-fix cleaning functions used in quality_checker.py, and loads the
result into clean_311_requests.

It uses a replace-load pattern, same as load_raw_to_postgres.py:
running it multiple times will not create duplicate rows.
"""

import sys
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from db_utils import get_postgres_connection

# Reuse the existing cleaning logic instead of duplicating it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from quality_checker import apply_auto_fixes


# Columns clean_311_requests actually stores, in insert order.
CLEAN_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "city",
    "status",
    "borough",
    "incident_zip_clean",
    "latitude",
    "longitude",
    "resolution_time",
]

BATCH_SIZE = 5000


def load_staging_data(cursor):
    """
    Reads all rows from stg_311_requests into a pandas DataFrame.
    """
    cursor.execute("""
        SELECT
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
            longitude
        FROM stg_311_requests;
    """)
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    return pd.DataFrame(rows, columns=columns)


def get_clean_table_count(cursor):
    """Returns the number of records currently stored in clean_311_requests."""
    cursor.execute("SELECT COUNT(*) FROM clean_311_requests;")
    return cursor.fetchone()[0]


def clear_clean_table(cursor):
    """Clears the clean table before loading fresh data."""
    cursor.execute("TRUNCATE TABLE clean_311_requests RESTART IDENTITY;")


def insert_clean_records(cursor, dataframe):
    """Inserts cleaned NYC 311 records into PostgreSQL."""
    insert_query = f"""
        INSERT INTO clean_311_requests (
            {", ".join(CLEAN_COLUMNS)}
        )
        VALUES %s;
    """

    # Convert pandas NaN/NaT into Python None so PostgreSQL stores them as NULL.
    prepared = dataframe[CLEAN_COLUMNS].astype(object).where(
        pd.notna(dataframe[CLEAN_COLUMNS]), None
    )

    records = [tuple(row) for row in prepared.to_numpy()]

    execute_values(cursor, insert_query, records, page_size=BATCH_SIZE)

    return len(records)


def main():
    """Runs the clean data loading process."""
    connection = None

    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            print("Loading staged data from stg_311_requests...")
            staged_df = load_staging_data(cursor)
            print(f"Staged records loaded: {len(staged_df)}")

            print("Applying cleaning functions...")
            cleaned_df, _ = apply_auto_fixes(staged_df)
            print(f"Cleaned dataset shape: {cleaned_df.shape}")

            records_before_load = get_clean_table_count(cursor)
            print(f"Records in clean_311_requests before load: {records_before_load}")

            clear_clean_table(cursor)
            print("Existing clean table records cleared.")

            inserted_records = insert_clean_records(cursor, cleaned_df)

            records_after_load = get_clean_table_count(cursor)

        connection.commit()

        print(f"Records inserted: {inserted_records}")
        print(f"Records after load: {records_after_load}")
        print("Clean data load completed successfully.")

    except Exception as error:
        if connection:
            connection.rollback()

        print("Clean data load failed.")
        print(f"Error: {error}")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()