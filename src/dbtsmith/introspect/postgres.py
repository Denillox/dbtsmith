"""
Postgres schema introspection: reads a real table's actual column
structure via information_schema, so generation is grounded in real
schema rather than plausible-sounding guesses.
"""

from dotenv import load_dotenv
import os
import psycopg

from dbtsmith.introspect.models import ColumnInfo, TableSchema

def _get_connection():
    # Fix re-reading .env file later
    load_dotenv()
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT')
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    db = os.getenv('POSTGRES_DB')

    return psycopg.connect(host=host, port=port, user=user, password=password, dbname=db)


def get_table_schema(table_name: str) -> TableSchema:
    """Introspect a real Postgres table and return its column schema."""
    with _get_connection() as conn:
        result = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", (table_name,))
        rows = result.fetchall()
        columns = [ColumnInfo(name=n, data_type=t) for n, t in rows]

        return TableSchema(table_name=table_name, columns=columns)