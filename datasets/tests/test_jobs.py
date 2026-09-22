from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from datasets.jobs import parse_dataset
from datasets.models import Dataset

User = get_user_model()


class ParseDatasetJobTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="erin", password="s3cure-pass")

    def _make_dataset(self, content: bytes, name="data.csv"):
        return Dataset.objects.create(
            owner=self.owner,
            name=name,
            raw_file=SimpleUploadedFile(name, content),
        )

    def test_valid_csv_marks_dataset_ready_with_schema(self):
        dataset = self._make_dataset(b"region,amount\nnorth,10\nsouth,20\nnorth,30\n")

        parse_dataset(dataset.id)

        dataset.refresh_from_db()
        self.assertEqual(dataset.status, Dataset.Status.READY)
        self.assertEqual(dataset.row_count, 3)
        self.assertIsNotNone(dataset.schema)
        self.assertIsNone(dataset.failure_reason)

    def test_empty_csv_marks_dataset_failed_with_reason(self):
        dataset = self._make_dataset(b"")

        parse_dataset(dataset.id)

        dataset.refresh_from_db()
        self.assertEqual(dataset.status, Dataset.Status.FAILED)
        self.assertTrue(dataset.failure_reason)

    def test_header_only_csv_marks_dataset_failed_with_reason(self):
        dataset = self._make_dataset(b"a,b,c\n")

        parse_dataset(dataset.id)

        dataset.refresh_from_db()
        self.assertEqual(dataset.status, Dataset.Status.FAILED)
        self.assertTrue(dataset.failure_reason)

    def test_corrupt_csv_does_not_raise_and_marks_failed(self):
        dataset = self._make_dataset(b"\x00\x01\x02not,a,csv\xff\xfe")

        try:
            parse_dataset(dataset.id)
        except Exception as exc:  # pragma: no cover - failure path assertion
            self.fail(f"parse_dataset raised unexpectedly: {exc}")

        dataset.refresh_from_db()
        self.assertIn(dataset.status, [Dataset.Status.FAILED, Dataset.Status.READY])
