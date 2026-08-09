import subprocess
from pathlib import Path

from dbtsmith.validate.models import CommandResult, ValidationResult


def _run_dbt_command(args: list[str], project_dir: Path) -> CommandResult:
    result = subprocess.run(
        args,
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    return CommandResult(
        command=" ".join(args),
        success=result.returncode == 0,
        output=result.stdout + result.stderr,
    )


def validate_project(project_dir: Path) -> ValidationResult:
    run_result = _run_dbt_command(
        ["dbt", "run", "--profiles-dir", "."], project_dir
    )

    if not run_result.success:
        return ValidationResult(run=run_result, test=None, success=False)

    test_result = _run_dbt_command(
        ["dbt", "test", "--profiles-dir", "."], project_dir
    )

    return ValidationResult(
        run=run_result,
        test=test_result,
        success=test_result.success,
    )