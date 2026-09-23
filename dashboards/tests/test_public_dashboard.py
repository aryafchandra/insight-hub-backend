from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Chart, Dashboard, ShareLink
from datasets.models import Dataset

User = get_user_model()


class PublicDashboardTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="wendy", password="s3cure-pass")
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            name="d.csv",
            raw_file=SimpleUploadedFile("d.csv", b"region,amount\nnorth,10\nsouth,20\n"),
            status=Dataset.Status.READY,
            schema=[{"name": "region", "type": "categorical"}, {"name": "amount", "type": "numeric"}],
            row_count=2,
        )
        self.dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Public Q1"
        )
        self.chart = Chart.objects.create(
            dashboard=self.dashboard,
            chart_type=Chart.ChartType.BAR,
            x_column="region",
            y_column="amount",
        )
        self.link = ShareLink.objects.create(dashboard=self.dashboard)

    def _url(self, token):
        return reverse("public-dashboards:public-dashboard-detail", args=[token])

    def test_no_auth_header_required(self):
        # APITestCase's client has no auth by default — this is implicit,
        # but assert explicitly that no credentials were ever set.
        response = self.client.get(self._url(self.link.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_includes_dashboard_charts_and_resolved_data(self):
        response = self.client.get(self._url(self.link.token))

        self.assertEqual(response.data["title"], "Public Q1")
        self.assertEqual(len(response.data["charts"]), 1)
        chart_payload = response.data["charts"][0]
        self.assertEqual(chart_payload["chart_type"], "bar")
        self.assertEqual(
            chart_payload["data"],
            [{"x": "north", "y": 10}, {"x": "south", "y": 20}],
        )

    def test_response_does_not_expose_raw_file_or_dataset(self):
        response = self.client.get(self._url(self.link.token))

        payload = str(response.data)
        self.assertNotIn("raw_file", payload)
        self.assertNotIn("dataset", payload)
        self.assertNotIn(".csv", payload)

    def test_nonexistent_token_returns_404(self):
        response = self.client.get(self._url("not-a-real-token"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoked_token_returns_404(self):
        self.link.revoked_at = timezone.now()
        self.link.save(update_fields=["revoked_at"])

        response = self.client.get(self._url(self.link.token))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_and_revoked_tokens_are_indistinguishable(self):
        self.link.revoked_at = timezone.now()
        self.link.save(update_fields=["revoked_at"])

        revoked_response = self.client.get(self._url(self.link.token))
        nonexistent_response = self.client.get(self._url("totally-made-up"))

        self.assertEqual(revoked_response.status_code, nonexistent_response.status_code)
        self.assertEqual(revoked_response.data, nonexistent_response.data)
