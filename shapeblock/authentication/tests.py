from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User


# Create your tests here.
class UserRegistrationTestCase(APITestCase):
    def setUp(self):
        self.register_url = reverse("rest_register")

    def test_user_registration(self):
        register_data = {
            "email": "testuser@example.com",
            "password1": "testpassword123",
            "password2": "testpassword123",
        }

        response = self.client.post(self.register_url, register_data, format="json")
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("email", response.data["user"])
        self.assertEqual(response.data["user"]["email"], register_data["email"])


class LoginTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123",
        )
        self.login_url = reverse("rest_login")

    def test_login(self):
        login_data = {
            "endpoint": "localhost",
            "email": "testuser@example.com",
            "password": "testpassword123",
        }
        # print(f"login data{login_data}")
        response = self.client.post(self.login_url, login_data, format="json")
        print(f"Response Data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    # def test_refresh_token(self):


# def get_token(self):


class LoginOutTestCase(APITestCase):
    def setUp(self):
        self.logout_url = reverse("rest_logout")

    def test_logout(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_login(self.user)
        response = self.client.post(self.logout_url)
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
