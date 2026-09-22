import pandas as pd

NUMERIC_MIN_RATIO = 0.95
DATE_MIN_RATIO = 0.95
MAX_CATEGORICAL_DISTINCT = 20


def infer_schema(df: pd.DataFrame) -> list[dict]:
    """Classify each column as numeric, date, categorical, or text.

    Uses a "coerce + flag" strategy for numeric/date columns: a column
    qualifies if at least NUMERIC_MIN_RATIO/DATE_MIN_RATIO of its non-null
    cells parse successfully. Cells that don't parse become null on coercion
    rather than forcing the whole column to `text`; the column is flagged
    `low_confidence` when not every non-null cell converted cleanly.
    """
    schema = []
    for name in df.columns:
        schema.append(_classify_column(name, df[name]))
    return schema


def _classify_column(name: str, series: pd.Series) -> dict:
    non_null = series.dropna()

    if len(non_null) == 0:
        return {"name": name, "type": "text"}

    numeric_ratio = _conversion_ratio(pd.to_numeric(non_null, errors="coerce"), len(non_null))
    if numeric_ratio >= NUMERIC_MIN_RATIO:
        entry = {"name": name, "type": "numeric"}
        if numeric_ratio < 1.0:
            entry["low_confidence"] = True
        return entry

    date_ratio = _conversion_ratio(
        pd.to_datetime(non_null, errors="coerce", format="mixed"), len(non_null)
    )
    if date_ratio >= DATE_MIN_RATIO:
        entry = {"name": name, "type": "date"}
        if date_ratio < 1.0:
            entry["low_confidence"] = True
        return entry

    distinct_count = non_null.nunique()
    threshold = min(MAX_CATEGORICAL_DISTINCT, 0.5 * len(non_null))
    if distinct_count < threshold:
        return {"name": name, "type": "categorical"}

    return {"name": name, "type": "text"}


def _conversion_ratio(converted: pd.Series, total: int) -> float:
    return converted.notna().sum() / total
