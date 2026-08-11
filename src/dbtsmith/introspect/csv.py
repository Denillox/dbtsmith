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


def get_table_schema(csv_path: str) -> TableSchema:
    # Introspect a CSV file and return its column schema

    '''
    Limitation: date-like columns are inferred as "text" and not "date,
    pandas doesn't detect dates without being told which columns to
    parse in advance. It works in practice cause Postgres casts
    text that looks like a date leniently when used in DATE_TRUNC(...),
    
    TODO: Try to detect dates properly using parse_dates=[...]
    '''

    path = Path(csv_path)

    df = pd.read_csv(path)

    columns = [
        ColumnInfo(name=name, data_type=_DTYPE_MAP.get(str(dtype), "text"))
        for name, dtype in df.dtypes.items()
    ]
    return TableSchema(table_name=path.stem, columns=columns)