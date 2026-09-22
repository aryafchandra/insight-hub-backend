from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase

from dashboards.models import Chart, Dashboard
from datasets.models import Dataset

User = get_user_model()


class DashboardModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="ida", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="sales.csv",
            raw_file=SimpleUploadedFile("sales.csv", b"a,b\n1,2\n"),
            status=Dataset.Status.READY,
            schema=[{"name": "a", "type": "numeric"}, {"name": "b", "type": "numeric"}],
            row_count=1,
        )

    def test_dashboard_has_uuid_primary_key(self):
        dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Q1 Sales"
        )

        self.assertEqual(len(str(dashboard.id)), 36)

    def test_deleting_dataset_with_dashboard_is_protected(self):
        Dashboard.objects.create(owner=self.owner, dataset=self.dataset, title="Q1 Sales")

        with self.assertRaises(IntegrityError):
            self.dataset.delete()


class ChartModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="jules", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="sales.csv",
            raw_file=SimpleUploadedFile("sales.csv", b"a,b\n1,2\n"),
            status=Dataset.Status.READY,
            schema=[{"name": "a", "type": "numeric"}, {"name": "b", "type": "numeric"}],
            row_count=1,
        )
        self.dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Q1 Sales"
        )

    def test_chart_defaults_layout_fields(self):
        chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )

        self.assertEqual(chart.x, 0)
        self.assertEqual(chart.y, 0)
        self.assertEqual(chart.z_index, 0)

    def test_deleting_dashboard_cascades_to_charts(self):
        chart = Chart.objects.create(
            dashboard=self.dashboard, chart_type=Chart.ChartType.BAR, x_column="a", y_column="b"
        )

        self.dashboard.delete()

        self.assertFalse(Chart.objects.filter(id=chart.id).exists())
