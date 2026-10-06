"""
Test PostgreSQL Connection for DataGuard

This script verifies that Python can connect to the local PostgreSQL
DataGuard database using the shared database utility module.
"""

from db_utils import get_postgres_connection


def test_database_connection():
    """
    Connects to PostgreSQL and prints the current database name.
    """
    connection = None

    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database();")
            current_database = cursor.fetchone()[0]

        print(f"Connected successfully. Current database: {current_database}")

    except Exception as error:
        print("Database connection failed.")
        print(f"Error: {error}")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    test_database_connection()