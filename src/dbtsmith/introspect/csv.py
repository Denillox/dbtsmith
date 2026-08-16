from pathlib import Path
import pandas as pd

from dbtsmith.introspect.models import ColumnInfo, TableSchema

_DTYPE_MAP = {
    "int64": "integer",
    "float64": "numeric",
    "object": "text",
    "datetime64[ns]": "date",
    "bool": "boolean",
}


def _looks_like_date(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    parsed = pd.to_datetime(non_null, format="%Y-%m-%d", errors="coerce")
    return bool(parsed.notna().all())


def get_table_schema(csv_path: str) -> TableSchema:
    path = Path(csv_path)
    df = pd.read_csv(path)

    columns = []
    for name, dtype in df.dtypes.items():
        mapped_type = _DTYPE_MAP.get(str(dtype), "text")
        if mapped_type == "text" and _looks_like_date(df[name]):
            mapped_type = "date"

        columns.append(ColumnInfo(name=name, data_type=mapped_type))

    return TableSchema(table_name=path.stem, columns=columns)