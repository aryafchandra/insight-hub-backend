from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datasets.models import Dataset

User = get_user_model()


class UploadDatasetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="frank", password="s3cure-pass")
        self.client.force_authenticate(user=self.user)

    def test_upload_returns_201_with_pending_status_without_parsing_inline(self):
        csv_file = SimpleUploadedFile("sales.csv", b"a,b\n1,2\n", content_type="text/csv")

        with patch("datasets.views.django_rq.get_queue") as mock_get_queue:
            response = self.client.post(
                reverse("datasets:dataset-list"), {"name": "sales.csv", "raw_file": csv_file}
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending")
        mock_get_queue.return_value.enqueue.assert_called_once()

        dataset = Dataset.objects.get(id=response.data["id"])
        self.assertEqual(dataset.status, Dataset.Status.PENDING)
        # Parsing happens in the worker, not the request — schema untouched.
        self.assertIsNone(dataset.schema)

    def test_upload_rejects_non_csv_file(self):
        txt_file = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")

        response = self.client.post(
            reverse("datasets:dataset-list"), {"name": "notes.txt", "raw_file": txt_file}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Dataset.objects.exists())

    def test_upload_rejects_unauthenticated_request(self):
        self.client.force_authenticate(user=None)
        csv_file = SimpleUploadedFile("sales.csv", b"a,b\n1,2\n", content_type="text/csv")

        response = self.client.post(
            reverse("datasets:dataset-list"), {"name": "sales.csv", "raw_file": csv_file}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
