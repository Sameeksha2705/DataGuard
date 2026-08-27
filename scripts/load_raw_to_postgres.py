"""
DataGuard Raw Data Loader

This script loads selected columns from the raw NYC 311 CSV file
into the PostgreSQL raw_311_requests table.
"""

import getpass
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


def load_raw_data():
    """
    Loads raw NYC 311 data from CSV into PostgreSQL.
    """
    project_root = Path(__file__).resolve().parent.parent
    raw_data_path = project_root / "data" / "nyc_311_raw_100k.csv"

    if not raw_data_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_data_path}")

    print("Loading raw CSV...")
    df = pd.read_csv(raw_data_path)

    columns_to_load = [
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
        "longitude"
    ]

    df_load = df[columns_to_load].copy()

    # Convert pandas missing values to Python None so PostgreSQL stores them as NULL.
    df_load = df_load.where(pd.notnull(df_load), None)

    print("Rows prepared for loading:", len(df_load))

    password = getpass.getpass("Enter PostgreSQL password: ")

    connection = psycopg2.connect(
        host="localhost",
        port=5432,
        database="dataguard",
        user="postgres",
        password=password
    )

    cursor = connection.cursor()

    insert_query = """
        INSERT INTO raw_311_requests (
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
        )
        VALUES %s
    """

    records = list(df_load.itertuples(index=False, name=None))

    print("Loading records into PostgreSQL...")
    execute_values(cursor, insert_query, records)

    connection.commit()

    print("Raw data loaded successfully.")
    print("Rows inserted:", len(records))

    cursor.close()
    connection.close()


if __name__ == "__main__":
    load_raw_data()