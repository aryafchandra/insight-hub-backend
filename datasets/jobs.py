import pandas as pd

from datasets.models import Dataset
from datasets.type_inference import infer_schema


def parse_dataset(dataset_id):
    """Background job: parse the uploaded CSV and update Dataset status.

    Runs in a django-rq worker, off the request cycle (see build spec §4a).
    """
    dataset = Dataset.objects.get(id=dataset_id)
    dataset.status = Dataset.Status.PROCESSING
    dataset.save(update_fields=["status"])

    try:
        with dataset.raw_file.open("rb") as fh:
            df = pd.read_csv(fh)
    except Exception as exc:
        _mark_failed(dataset, f"Could not read file as CSV: {exc}")
        return

    if df.shape[1] == 0:
        _mark_failed(dataset, "CSV has no columns.")
        return

    if len(df) == 0:
        _mark_failed(dataset, "CSV has no data rows.")
        return

    schema = infer_schema(df)

    dataset.schema = schema
    dataset.row_count = len(df)
    dataset.status = Dataset.Status.READY
    dataset.failure_reason = None
    dataset.save(update_fields=["schema", "row_count", "status", "failure_reason"])


def _mark_failed(dataset, reason):
    dataset.status = Dataset.Status.FAILED
    dataset.failure_reason = reason
    dataset.save(update_fields=["status", "failure_reason"])
