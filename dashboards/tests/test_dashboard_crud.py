from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Dashboard
from datasets.models import Dataset

User = get_user_model()


class DashboardCRUDTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="kate", password="s3cure-pass")
        self.other = User.objects.create_user(username="liam", password="s3cure-pass")
        self.ready_dataset = self._make_dataset(self.owner, status=Dataset.Status.READY)
        self.pending_dataset = self._make_dataset(self.owner, status=Dataset.Status.PENDING)
        self.other_dataset = self._make_dataset(self.other, status=Dataset.Status.READY)
        self.client.force_authenticate(user=self.owner)

    def _make_dataset(self, owner, status):
        return Dataset.objects.create(
            owner=owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", b"a,b\n1,2\n"),
            status=status,
            schema=[{"name": "a", "type": "numeric"}, {"name": "b", "type": "numeric"}]
            if status == Dataset.Status.READY
            else None,
            row_count=1 if status == Dataset.Status.READY else None,
        )

    def test_create_dashboard_from_ready_dataset(self):
        response = self.client.post(
            reverse("dashboards:dashboard-list"),
            {"title": "Q1", "dataset": str(self.ready_dataset.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Dashboard.objects.filter(title="Q1", owner=self.owner).exists())

    def test_create_dashboard_rejects_non_ready_dataset(self):
        response = self.client.post(
            reverse("dashboards:dashboard-list"),
            {"title": "Q1", "dataset": str(self.pending_dataset.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dashboard_rejects_dataset_owned_by_someone_else(self):
        response = self.client.post(
            reverse("dashboards:dashboard-list"),
            {"title": "Q1", "dataset": str(self.other_dataset.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_only_owned_dashboards(self):
        Dashboard.objects.create(owner=self.owner, dataset=self.ready_dataset, title="Mine")
        Dashboard.objects.create(owner=self.other, dataset=self.other_dataset, title="Theirs")

        response = self.client.get(reverse("dashboards:dashboard-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [d["title"] for d in response.data]
        self.assertEqual(titles, ["Mine"])

    def test_retrieve_includes_nested_charts(self):
        dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.ready_dataset, title="Q1"
        )

        response = self.client.get(reverse("dashboards:dashboard-detail", args=[dashboard.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["charts"], [])

    def test_patch_updates_title(self):
        dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.ready_dataset, title="Old"
        )

        response = self.client.patch(
            reverse("dashboards:dashboard-detail", args=[dashboard.id]), {"title": "New"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dashboard.refresh_from_db()
        self.assertEqual(dashboard.title, "New")

    def test_delete_removes_dashboard(self):
        dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.ready_dataset, title="Gone"
        )

        response = self.client.delete(reverse("dashboards:dashboard-detail", args=[dashboard.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Dashboard.objects.filter(id=dashboard.id).exists())

    def test_other_users_dashboard_returns_404(self):
        dashboard = Dashboard.objects.create(
            owner=self.other, dataset=self.other_dataset, title="Theirs"
        )

        response = self.client.get(reverse("dashboards:dashboard-detail", args=[dashboard.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("dashboards:dashboard-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
