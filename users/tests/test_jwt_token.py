from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class JwtTokenEndpointTests(APITestCase):
    def test_obtain_jwt_token_successfully(self):
        username = "jwt_user"
        password = "strongpass123"
        User.objects.create_user(username=username, password=password)

        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": username, "password": password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])
