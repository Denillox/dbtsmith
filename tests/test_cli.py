from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from dbtsmith.cli import generate
from dbtsmith.ir.models import TransformationIR
from dbtsmith.validate.models import ValidationResult, CommandResult


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
        ],
        output={"name": "monthly_customer_orders"},
    )


@patch("dbtsmith.cli.validate_project")
@patch("dbtsmith.cli.generate_schema_yml")
@patch("dbtsmith.cli.generate_mart_model")
@patch("dbtsmith.cli.generate_staging_model")
@patch("dbtsmith.cli.get_postgres_schema")
@patch("dbtsmith.cli.parse_instruction")
def test_cli_success_path(
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

    runner = CliRunner()
    result = runner.invoke(generate, [
        "--source", "orders",
        "--instruction", "dedupe by email, join with customers, aggregate order totals by month",
        "--output", "monthly_customer_orders",
        "--join", "customers",
        "--output-dir", str(tmp_path),
    ])

    assert result.exit_code == 0
    assert "Success" in result.output
    mock_parse.assert_called_once()


@patch("dbtsmith.cli.validate_project")
@patch("dbtsmith.cli.generate_schema_yml")
@patch("dbtsmith.cli.generate_mart_model")
@patch("dbtsmith.cli.generate_staging_model")
@patch("dbtsmith.cli.get_postgres_schema")
@patch("dbtsmith.cli.parse_instruction")
def test_cli_reports_validation_failure(
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
    test=CommandResult(command="dbt test", success=False, output="FAIL not_null_stg_orders_email"),
    success=False,
)

    runner = CliRunner()
    result = runner.invoke(generate, [
        "--source", "orders",
        "--instruction", "dedupe by email, join with customers, aggregate order totals by month",
        "--output", "monthly_customer_orders",
        "--join", "customers",
        "--output-dir", str(tmp_path),
    ])

    assert result.exit_code == 1
    assert "Validation failed" in result.output
    assert "not_null_stg_orders_email" in result.output

@patch("dbtsmith.cli.validate_project")
@patch("dbtsmith.cli.generate_schema_yml")
@patch("dbtsmith.cli.generate_mart_model")
@patch("dbtsmith.cli.generate_staging_model")
@patch("dbtsmith.cli.get_postgres_schema")
@patch("dbtsmith.cli.parse_instruction")
def test_cli_skips_mart_when_no_join(
    mock_parse, mock_get_schema, mock_staging, mock_mart, mock_schema_yml, mock_validate,
    tmp_path,
):
    mock_parse.return_value = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
        ],
        output={"name": "some_output"},
    )

    mock_get_schema.return_value = MagicMock()
    mock_staging.return_value = "SELECT 1"
    mock_schema_yml.return_value = "version: 2"
    mock_validate.return_value = ValidationResult(
        seed=CommandResult(command="dbt seed", success=True, output="ok"),
        run=CommandResult(command="dbt run", success=True, output="ok"),
        test=CommandResult(command="dbt test", success=True, output="ok"),
        success=True,
    )

    runner = CliRunner()
    result = runner.invoke(generate, [
        "--source", "orders",
        "--instruction", "dedupe by email",
        "--output", "some_output",
        "--output-dir", str(tmp_path),
    ])

    assert result.exit_code == 0
    mock_mart.assert_not_called()