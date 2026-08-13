from unittest.mock import patch, MagicMock
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dbtsmith.ir.models import TransformationIR
from dbtsmith.validate.models import ValidationResult, CommandResult

APP_PATH = str(Path(__file__).parent.parent / "src" / "dbtsmith" / "ui" / "app.py")



def _fake_ir():
    return TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "email", "right_column": "email"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "order_date", "granularity": "month"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total"}
                ],
            },
        ],
        output={"name": "monthly_customer_orders"},
    )


@patch("dbtsmith.validate.dbt.validate_project")
@patch("dbtsmith.generate.schema.generate_schema_yml")
@patch("dbtsmith.generate.mart.generate_mart_model")
@patch("dbtsmith.generate.staging.generate_staging_model")
@patch("dbtsmith.introspect.postgres.get_table_schema")
@patch("dbtsmith.ir.parse.parse_instruction")
def test_app_success_path(
    mock_parse, mock_get_schema, mock_staging, mock_mart, mock_schema_yml, mock_validate,
    tmp_path,
):
    mock_parse.return_value = _fake_ir()
    mock_get_schema.return_value = MagicMock()
    mock_staging.return_value = "SELECT 1"
    mock_mart.return_value = "SELECT 2"
    mock_schema_yml.return_value = "version: 2"
    mock_validate.return_value = ValidationResult(
        seed=CommandResult(command="dbt seed", success=True, output="ok"),
        run=CommandResult(command="dbt run", success=True, output="ok"),
        test=CommandResult(command="dbt test", success=True, output="ok"),
        success=True,
    )

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("orders")           
    at.text_area[0].input("dedupe by email, join with customers, aggregate order totals by month")                                         
    at.text_input[1].input("monthly_customer_orders")  
    at.text_input[2].input("customers")         
    at.text_input[3].input(str(tmp_path))        

    at.button[0].click().run()

    assert not at.exception
    assert len(at.success) == 1
    assert "passed" in at.success[0].value