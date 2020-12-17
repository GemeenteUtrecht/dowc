from rest_framework import status
from rest_framework.test import APITestCase


class SchemaTests(APITestCase):
    def test_schema_served(self):
        response = self.client.get("/api/v1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
