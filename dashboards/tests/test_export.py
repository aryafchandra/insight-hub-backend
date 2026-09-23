from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Dashboard
from datasets.models import Dataset

User = get_user_model()

CSV_CONTENT = b"region,amount\nnorth,10\nsouth,20\n"


class DashboardExportTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="bella", password="s3cure-pass")
        self.other = User.objects.create_user(username="carl", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="export.csv",
            raw_file=SimpleUploadedFile("export.csv", CSV_CONTENT),
            status=Dataset.Status.READY,
            schema=[{"name": "region", "type": "categorical"}, {"name": "amount", "type": "numeric"}],
            row_count=2,
        )
        self.dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Export Test"
        )
        self.client.force_authenticate(user=self.owner)

    def _url(self):
        return reverse("dashboards:dashboard-export", args=[self.dashboard.id])

    def test_export_returns_original_csv_bytes(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = b"".join(response.streaming_content)
        self.assertEqual(content, CSV_CONTENT)

    def test_export_sets_content_disposition_attachment(self):
        response = self.client.get(self._url())

        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("export.csv", response["Content-Disposition"])

    def test_export_by_non_owner_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_of_deleted_dashboard_returns_404(self):
        self.client.delete(reverse("dashboards:dashboard-detail", args=[self.dashboard.id]))

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
