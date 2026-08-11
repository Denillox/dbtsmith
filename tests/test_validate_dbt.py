from pathlib import Path

import psycopg
import pytest

from dbtsmith.validate.dbt import validate_project

PROJECT_DIR = Path("generated_project")


def _get_connection():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )


def test_validate_project_success():
    result = validate_project(PROJECT_DIR)
    assert result.success is True
    assert result.seed.success is True
    assert result.run.success is True
    assert result.test.success is True


def test_validate_project_reports_real_failure():
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO orders (id, customer_id, email, order_total, order_date) "
            "VALUES (999, 1, NULL, 50.00, '2025-03-01')"
        )
        conn.commit()

        result = validate_project(PROJECT_DIR)

        assert result.success is False
        assert result.run.success is True
        assert result.test.success is False
        assert "not_null_stg_orders_email" in result.test.output
        assert result.seed.success is True
    finally:
        conn.execute("DELETE FROM orders WHERE id = 999")
        conn.commit()
        conn.close()