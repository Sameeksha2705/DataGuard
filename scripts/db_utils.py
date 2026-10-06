"""
DataGuard Database Utilities

This module centralizes PostgreSQL connection logic for the DataGuard project.

Database settings can be provided through environment variables.
If the PostgreSQL password is not provided through an environment variable,
the script asks for it securely at runtime.
"""

import getpass
import os

import psycopg2


DB_HOST = os.getenv("DATAGUARD_DB_HOST", "localhost")
DB_PORT = int(os.getenv("DATAGUARD_DB_PORT", "5432"))
DB_NAME = os.getenv("DATAGUARD_DB_NAME", "dataguard")
DB_USER = os.getenv("DATAGUARD_DB_USER", "postgres")


def get_database_password():
    """
    Gets the PostgreSQL password from an environment variable if available.
    Otherwise, asks the user to enter it securely.
    """
    password = os.getenv("DATAGUARD_DB_PASSWORD")

    if password:
        return password

    return getpass.getpass("Enter PostgreSQL password: ")


def get_postgres_connection():
    """
    Creates and returns a PostgreSQL connection for the DataGuard database.
    """
    password = get_database_password()

    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=password
    )

    return connection