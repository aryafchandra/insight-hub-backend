from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Chart, Dashboard
from datasets.models import Dataset

User = get_user_model()


class ChartCRUDTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="mona", password="s3cure-pass")
        self.other = User.objects.create_user(username="noah", password="s3cure-pass")
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
        self.client.force_authenticate(user=self.owner)

    def _create_url(self):
        return reverse("dashboards:chart-create", args=[self.dashboard.id])

    def test_create_chart_with_valid_columns(self):
        response = self.client.post(
            self._create_url(),
            {"chart_type": "bar", "x_column": "a", "y_column": "b"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Chart.objects.filter(dashboard=self.dashboard).exists())

    def test_create_chart_rejects_unknown_x_column(self):
        response = self.client.post(
            self._create_url(),
            {"chart_type": "bar", "x_column": "nope", "y_column": "b"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_chart_rejects_unknown_y_column(self):
        response = self.client.post(
            self._create_url(),
            {"chart_type": "bar", "x_column": "a", "y_column": "nope"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_chart_on_someone_elses_dashboard_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            self._create_url(),
            {"chart_type": "bar", "x_column": "a", "y_column": "b"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_layout_fields(self):
        chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )

        response = self.client.patch(
            reverse("charts:chart-detail", args=[chart.id]), {"x": 10, "y": 20}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chart.refresh_from_db()
        self.assertEqual(chart.x, 10)
        self.assertEqual(chart.y, 20)

    def test_delete_removes_chart(self):
        chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )

        response = self.client.delete(reverse("charts:chart-detail", args=[chart.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Chart.objects.filter(id=chart.id).exists())

    def test_updating_someone_elses_chart_returns_404(self):
        chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(reverse("charts:chart-detail", args=[chart.id]), {"x": 5})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
