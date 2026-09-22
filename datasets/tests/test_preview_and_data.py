from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datasets.models import Dataset

User = get_user_model()

CSV_CONTENT = (
    b"region,amount\n"
    + b"".join(f"r{i},{i}\n".encode() for i in range(30))
)


class DatasetPreviewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="oscar", password="s3cure-pass")
        self.other = User.objects.create_user(username="paul", password="s3cure-pass")
        self.client.force_authenticate(user=self.owner)

    def _make_dataset(self, owner=None, status_=Dataset.Status.READY):
        return Dataset.objects.create(
            owner=owner or self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", CSV_CONTENT),
            status=status_,
            schema=[{"name": "region", "type": "categorical"}, {"name": "amount", "type": "numeric"}]
            if status_ == Dataset.Status.READY
            else None,
            row_count=30 if status_ == Dataset.Status.READY else None,
        )

    def test_preview_returns_bounded_sample(self):
        dataset = self._make_dataset()

        response = self.client.get(reverse("datasets:dataset-preview", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 20)
        self.assertEqual(response.data[0], {"region": "r0", "amount": 0})

    def test_preview_rejects_non_ready_dataset(self):
        dataset = self._make_dataset(status_=Dataset.Status.PENDING)

        response = self.client.get(reverse("datasets:dataset-preview", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_of_someone_elses_dataset_returns_404(self):
        dataset = self._make_dataset(owner=self.other)

        response = self.client.get(reverse("datasets:dataset-preview", args=[dataset.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DatasetDataTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="quinn", password="s3cure-pass")
        self.client.force_authenticate(user=self.owner)
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", CSV_CONTENT),
            status=Dataset.Status.READY,
            schema=[{"name": "region", "type": "categorical"}, {"name": "amount", "type": "numeric"}],
            row_count=30,
        )

    def test_data_returns_only_requested_columns(self):
        response = self.client.get(
            reverse("datasets:dataset-data", args=[self.dataset.id]), {"x": "region", "y": "amount"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 30)
        self.assertEqual(response.data[0], {"x": "r0", "y": 0})
        self.assertEqual(set(response.data[0].keys()), {"x", "y"})

    def test_data_rejects_unknown_column(self):
        response = self.client.get(
            reverse("datasets:dataset-data", args=[self.dataset.id]), {"x": "region", "y": "nope"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_data_requires_both_params(self):
        response = self.client.get(
            reverse("datasets:dataset-data", args=[self.dataset.id]), {"x": "region"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
