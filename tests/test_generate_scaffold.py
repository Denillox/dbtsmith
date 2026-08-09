from pathlib import Path

import yaml

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.scaffold import scaffold_project


def _make_ir():
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


def test_scaffold_project_creates_structure(tmp_path):
    ir = _make_ir()
    scaffold_project(ir, tmp_path)

    assert (tmp_path / "dbt_project.yml").exists()
    assert (tmp_path / "profiles.yml").exists()
    assert (tmp_path / "models" / "staging" / "sources.yml").exists()
    assert (tmp_path / "models" / "marts").is_dir()


def test_scaffold_project_sources_include_join_targets(tmp_path):
    ir = _make_ir()
    scaffold_project(ir, tmp_path)

    sources = yaml.safe_load((tmp_path / "models" / "staging" / "sources.yml").read_text())
    table_names = {t["name"] for t in sources["sources"][0]["tables"]}

    assert table_names == {"orders", "customers"}