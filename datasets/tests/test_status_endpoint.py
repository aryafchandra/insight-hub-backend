from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datasets.models import Dataset

User = get_user_model()


class DatasetStatusEndpointTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="gina", password="s3cure-pass")
        self.other = User.objects.create_user(username="hank", password="s3cure-pass")

    def _make_dataset(self, **overrides):
        defaults = {
            "owner": self.owner,
            "name": "data.csv",
            "raw_file": SimpleUploadedFile("data.csv", b"a,b\n1,2\n"),
        }
        defaults.update(overrides)
        return Dataset.objects.create(**defaults)

    def test_pending_dataset_returns_status_without_schema(self):
        dataset = self._make_dataset(status=Dataset.Status.PENDING)
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse("datasets:dataset-detail", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "pending")
        self.assertNotIn("schema", response.data)

    def test_ready_dataset_returns_schema_and_row_count(self):
        dataset = self._make_dataset(
            status=Dataset.Status.READY,
            schema=[{"name": "a", "type": "numeric"}],
            row_count=1,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse("datasets:dataset-detail", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["schema"], [{"name": "a", "type": "numeric"}])
        self.assertEqual(response.data["row_count"], 1)

    def test_failed_dataset_returns_failure_reason(self):
        dataset = self._make_dataset(
            status=Dataset.Status.FAILED, failure_reason="Empty file"
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse("datasets:dataset-detail", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["failure_reason"], "Empty file")

    def test_other_users_dataset_returns_404(self):
        dataset = self._make_dataset()
        self.client.force_authenticate(user=self.other)

        response = self.client.get(reverse("datasets:dataset-detail", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_returns_401(self):
        dataset = self._make_dataset()

        response = self.client.get(reverse("datasets:dataset-detail", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
