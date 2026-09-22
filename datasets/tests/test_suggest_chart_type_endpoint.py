from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datasets.models import Dataset

User = get_user_model()

CSV_CONTENT = b"region,amount,signup_date\nnorth,10,2024-01-01\nsouth,20,2024-01-02\n"
SCHEMA = [
    {"name": "region", "type": "categorical"},
    {"name": "amount", "type": "numeric"},
    {"name": "signup_date", "type": "date"},
]


class SuggestChartTypeEndpointTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="sasha", password="s3cure-pass")
        self.other = User.objects.create_user(username="theo", password="s3cure-pass")
        self.client.force_authenticate(user=self.owner)
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", CSV_CONTENT),
            status=Dataset.Status.READY,
            schema=SCHEMA,
            row_count=2,
        )

    def _url(self):
        return reverse("datasets:dataset-suggest-chart-type", args=[self.dataset.id])

    def test_categorical_and_numeric_suggests_bar(self):
        response = self.client.get(self._url(), {"x": "region", "y": "amount"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggested_chart_type"], "bar")

    def test_date_and_numeric_suggests_line(self):
        response = self.client.get(self._url(), {"x": "signup_date", "y": "amount"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggested_chart_type"], "line")

    def test_x_only_categorical_suggests_pie(self):
        response = self.client.get(self._url(), {"x": "region"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggested_chart_type"], "pie")

    def test_missing_x_returns_400(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_column_returns_400(self):
        response = self.client.get(self._url(), {"x": "nope"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_ready_dataset_returns_400(self):
        pending = Dataset.objects.create(
            owner=self.owner,
            name="p.csv",
            raw_file=SimpleUploadedFile("p.csv", CSV_CONTENT),
            status=Dataset.Status.PENDING,
        )

        response = self.client.get(
            reverse("datasets:dataset-suggest-chart-type", args=[pending.id]), {"x": "region"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_users_dataset_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self._url(), {"x": "region"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self._url(), {"x": "region"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
