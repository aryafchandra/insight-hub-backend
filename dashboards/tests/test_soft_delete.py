from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Chart, Dashboard, ShareLink
from datasets.models import Dataset

User = get_user_model()


class DashboardSoftDeleteTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="zack", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", b"a,b\n1,2\n"),
            status=Dataset.Status.READY,
            schema=[{"name": "a", "type": "numeric"}, {"name": "b", "type": "numeric"}],
            row_count=1,
        )
        self.dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Q1"
        )
        self.chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )
        self.client.force_authenticate(user=self.owner)

    def _url(self):
        return reverse("dashboards:dashboard-detail", args=[self.dashboard.id])

    def test_delete_returns_204(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_flags_row_instead_of_removing_it(self):
        self.client.delete(self._url())

        still_there = Dashboard.all_objects.get(id=self.dashboard.id)
        self.assertIsNotNone(still_there.deleted_at)

    def test_deleted_dashboard_404s_on_get(self):
        self.client.delete(self._url())

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_dashboards_chart_404s_too(self):
        # The join-filter gotcha: Chart.objects doesn't automatically
        # inherit Dashboard's soft-delete filtering.
        self.client.delete(self._url())

        response = self.client.patch(
            reverse("charts:chart-detail", args=[self.chart.id]), {"x": 5}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_dashboards_share_link_stops_resolving(self):
        # The other join-filter gotcha: ShareLink lookups don't automatically
        # inherit Dashboard's soft-delete filtering either.
        link = ShareLink.objects.create(dashboard=self.dashboard)

        self.client.delete(self._url())

        self.client.force_authenticate(user=None)
        response = self.client.get(
            reverse("public-dashboards:public-dashboard-detail", args=[link.token])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_someone_elses_dashboard_returns_404(self):
        other = User.objects.create_user(username="amir", password="s3cure-pass")
        self.client.force_authenticate(user=other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
