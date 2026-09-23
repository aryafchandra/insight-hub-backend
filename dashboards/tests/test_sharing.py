from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboards.models import Dashboard, ShareLink
from datasets.models import Dataset

User = get_user_model()


class ShareLinkGenerationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="uma", password="s3cure-pass")
        self.other = User.objects.create_user(username="victor", password="s3cure-pass")
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

    def _share_url(self):
        return reverse("dashboards:dashboard-share", args=[self.dashboard.id])

    def _regenerate_url(self):
        return reverse("dashboards:dashboard-share-regenerate", args=[self.dashboard.id])

    def test_first_call_creates_link_and_returns_201(self):
        response = self.client.post(self._share_url())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ShareLink.objects.filter(dashboard=self.dashboard).count(), 1)
        self.assertEqual(len(response.data["token"]), 32)

    def test_calling_again_returns_same_token_without_duplicating(self):
        first = self.client.post(self._share_url())
        second = self.client.post(self._share_url())

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["token"], second.data["token"])
        self.assertEqual(ShareLink.objects.filter(dashboard=self.dashboard).count(), 1)

    def test_tokens_for_different_dashboards_are_not_sequential(self):
        other_dashboard = Dashboard.objects.create(
            owner=self.owner, dataset=self.dataset, title="Q2"
        )

        token_a = self.client.post(self._share_url()).data["token"]
        token_b = self.client.post(
            reverse("dashboards:dashboard-share", args=[other_dashboard.id])
        ).data["token"]

        self.assertNotEqual(token_a, token_b)
        # Not sequential integers / incrementing IDs.
        self.assertFalse(token_a.isdigit())
        self.assertFalse(token_b.isdigit())

    def test_share_on_unowned_dashboard_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(self._share_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self._share_url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regenerate_returns_new_token_and_revokes_old(self):
        old_token = self.client.post(self._share_url()).data["token"]

        response = self.client.post(self._regenerate_url())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_token = response.data["token"]
        self.assertNotEqual(old_token, new_token)

        old_link = ShareLink.objects.get(token=old_token)
        self.assertIsNotNone(old_link.revoked_at)
        new_link = ShareLink.objects.get(token=new_token)
        self.assertIsNone(new_link.revoked_at)

    def test_regenerate_old_token_stops_resolving_publicly(self):
        old_token = self.client.post(self._share_url()).data["token"]
        self.client.post(self._regenerate_url())

        self.client.force_authenticate(user=None)
        response = self.client.get(
            reverse("public-dashboards:public-dashboard-detail", args=[old_token])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_regenerate_works_when_no_link_exists_yet(self):
        response = self.client.post(self._regenerate_url())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regenerate_on_unowned_dashboard_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(self._regenerate_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
