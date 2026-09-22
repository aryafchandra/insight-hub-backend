from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    def test_register_creates_user_and_returns_201(self):
        url = reverse("accounts:register")
        response = self.client.post(
            url,
            {"username": "alice", "email": "alice@example.com", "password": "s3cure-pass"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="alice").exists())
        self.assertNotIn("password", response.data)

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username="alice", password="s3cure-pass")
        url = reverse("accounts:register")

        response = self.client.post(
            url,
            {"username": "alice", "email": "alice2@example.com", "password": "s3cure-pass"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="s3cure-pass")

    def test_login_with_valid_credentials_returns_tokens(self):
        url = reverse("accounts:login")

        response = self.client.post(url, {"username": "bob", "password": "s3cure-pass"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_invalid_credentials_is_rejected(self):
        url = reverse("accounts:login")

        response = self.client.post(url, {"username": "bob", "password": "wrong"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access_token(self):
        login_url = reverse("accounts:login")
        login_response = self.client.post(login_url, {"username": "bob", "password": "s3cure-pass"})
        refresh_token = login_response.data["refresh"]

        refresh_url = reverse("accounts:refresh")
        response = self.client.post(refresh_url, {"refresh": refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class AuthenticatedRequestTests(APITestCase):
    def test_request_without_token_is_rejected(self):
        # /datasets/ requires auth; used here purely to prove the JWT
        # authentication class is wired up project-wide.
        response = self.client.get(reverse("datasets:dataset-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_with_valid_token_populates_request_user(self):
        user = User.objects.create_user(username="carol", password="s3cure-pass")
        login_response = self.client.post(
            reverse("accounts:login"), {"username": "carol", "password": "s3cure-pass"}
        )
        access = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get(reverse("datasets:dataset-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
