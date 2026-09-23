from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datasets.models import Dataset

User = get_user_model()


class DatasetSoftDeleteTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="xena", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", b"a,b\n1,2\n"),
            status=Dataset.Status.READY,
            schema=[{"name": "a", "type": "numeric"}, {"name": "b", "type": "numeric"}],
            row_count=1,
        )
        self.client.force_authenticate(user=self.owner)

    def _url(self):
        return reverse("datasets:dataset-detail", args=[self.dataset.id])

    def test_delete_returns_204(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_flags_row_instead_of_removing_it(self):
        self.client.delete(self._url())

        still_there = Dataset.all_objects.get(id=self.dataset.id)
        self.assertIsNotNone(still_there.deleted_at)

    def test_deleted_dataset_404s_on_get(self):
        self.client.delete(self._url())

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_dataset_missing_from_list(self):
        self.client.delete(self._url())

        response = self.client.get(reverse("datasets:dataset-list"))

        self.assertEqual(response.data, [])

    def test_deleted_dataset_cannot_back_a_new_dashboard(self):
        self.client.delete(self._url())

        response = self.client.post(
            reverse("dashboards:dashboard-list"),
            {"title": "Q1", "dataset": str(self.dataset.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_someone_elses_dataset_returns_404(self):
        other = User.objects.create_user(username="yusuf", password="s3cure-pass")
        self.client.force_authenticate(user=other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
