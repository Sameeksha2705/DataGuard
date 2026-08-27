"""
DataGuard PostgreSQL Connection Test

This script checks whether Python can connect to the local DataGuard PostgreSQL database.
"""

import getpass
import psycopg2


def test_connection():
    """
    Connects to the local PostgreSQL DataGuard database and runs a test query.
    """
    password = getpass.getpass("Enter PostgreSQL password: ")

    connection = psycopg2.connect(
        host="localhost",
        port=5432,
        database="dataguard",
        user="postgres",
        password=password
    )

    cursor = connection.cursor()

    cursor.execute("SELECT current_database();")
    database_name = cursor.fetchone()[0]

    print("Connected successfully.")
    print("Current database:", database_name)

    cursor.close()
    connection.close()


if __name__ == "__main__":
    test_connection()

    