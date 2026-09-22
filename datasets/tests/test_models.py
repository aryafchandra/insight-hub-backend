from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from datasets.models import Dataset

User = get_user_model()


class DatasetModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="dana", password="s3cure-pass")

    def _make_dataset(self, **overrides):
        defaults = {
            "owner": self.owner,
            "name": "sales.csv",
            "raw_file": SimpleUploadedFile("sales.csv", b"a,b\n1,2\n"),
        }
        defaults.update(overrides)
        return Dataset.objects.create(**defaults)

    def test_defaults_to_pending_status(self):
        dataset = self._make_dataset()

        self.assertEqual(dataset.status, Dataset.Status.PENDING)

    def test_schema_and_row_count_are_nullable(self):
        dataset = self._make_dataset()

        self.assertIsNone(dataset.schema)
        self.assertIsNone(dataset.row_count)

    def test_has_uuid_primary_key(self):
        dataset = self._make_dataset()

        self.assertEqual(len(str(dataset.id)), 36)
