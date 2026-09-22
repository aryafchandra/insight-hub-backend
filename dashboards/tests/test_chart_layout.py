from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Chart, Dashboard
from datasets.models import Dataset

User = get_user_model()


class ChartLayoutPatchTests(APITestCase):
    """TICKET-301: lightweight, idempotent layout-only PATCH /charts/:id/."""

    def setUp(self):
        self.owner = User.objects.create_user(username="riley", password="s3cure-pass")
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
            dashboard=self.dashboard,
            chart_type=Chart.ChartType.BAR,
            x_column="a",
            y_column="b",
            narrative="original narrative",
        )
        self.client.force_authenticate(user=self.owner)

    def _url(self):
        return reverse("charts:chart-detail", args=[self.chart.id])

    def test_position_only_patch_leaves_size_and_config_untouched(self):
        response = self.client.patch(self._url(), {"x": 100, "y": 50})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chart.refresh_from_db()
        self.assertEqual(self.chart.x, 100)
        self.assertEqual(self.chart.y, 50)
        self.assertEqual(self.chart.width, 400)
        self.assertEqual(self.chart.height, 300)
        self.assertEqual(self.chart.chart_type, Chart.ChartType.BAR)
        self.assertEqual(self.chart.x_column, "a")
        self.assertEqual(self.chart.narrative, "original narrative")

    def test_size_only_patch_leaves_position_and_config_untouched(self):
        response = self.client.patch(self._url(), {"width": 600, "height": 450})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chart.refresh_from_db()
        self.assertEqual(self.chart.width, 600)
        self.assertEqual(self.chart.height, 450)
        self.assertEqual(self.chart.x, 0)
        self.assertEqual(self.chart.y, 0)
        self.assertEqual(self.chart.chart_type, Chart.ChartType.BAR)

    def test_layout_patch_does_not_require_x_column_or_y_column(self):
        # Regression guard: a layout-only payload must never trip the
        # column-validation logic in ChartSerializer.validate(), even
        # though x_column/y_column are otherwise-required model fields.
        response = self.client.patch(self._url(), {"z_index": 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chart.refresh_from_db()
        self.assertEqual(self.chart.z_index, 3)

    def test_repeated_identical_patch_is_idempotent(self):
        first = self.client.patch(self._url(), {"x": 25, "y": 75})
        second = self.client.patch(self._url(), {"x": 25, "y": 75})

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["x"], second.data["x"])
        self.assertEqual(first.data["y"], second.data["y"])
        self.chart.refresh_from_db()
        self.assertEqual(self.chart.x, 25)
        self.assertEqual(self.chart.y, 75)

    def test_patch_rejects_zero_width(self):
        response = self.client.patch(self._url(), {"width": 0})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rejects_negative_height(self):
        response = self.client.patch(self._url(), {"height": -10})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
