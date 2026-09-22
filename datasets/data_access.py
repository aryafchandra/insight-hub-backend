import pandas as pd

PREVIEW_ROW_LIMIT = 20


def read_preview(dataset):
    """First PREVIEW_ROW_LIMIT rows of a ready dataset's CSV, as records."""
    with dataset.raw_file.open("rb") as fh:
        df = pd.read_csv(fh, nrows=PREVIEW_ROW_LIMIT)
    return df.where(pd.notna(df), None).to_dict(orient="records")


def read_columns(dataset, x_column, y_column):
    """Resolved {x, y} points for the two requested columns only."""
    with dataset.raw_file.open("rb") as fh:
        df = pd.read_csv(fh, usecols=[x_column, y_column])
    df = df.where(pd.notna(df), None)
    return [
        {"x": row[x_column], "y": row[y_column]}
        for row in df.to_dict(orient="records")
    ]
