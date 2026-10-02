"""
Тесты для представлений CRM PlayStation Club.
"""
from django.test import TestCase, Client
from django.urls import reverse
from crm_core.models import Place, Tariff


class DashboardViewTest(TestCase):
    """Тесты дашборда."""

    def setUp(self):
        self.client = Client()

    def test_landing_page(self):
        """Тест главной страницы."""
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])

    def test_operations_dashboard(self):
        """Тест операционного дашборда."""
        response = self.client.get('/dashboard/')
        self.assertIn(response.status_code, [200, 302])


class APITest(TestCase):
    """Тесты API."""

    def setUp(self):
        self.client = Client()
        self.tariff = Tariff.objects.create(
            name="Test",
            hourly_rate=100.0
        )
        self.place = Place.objects.create(
            name="Test Place",
            place_type="Basic",
            status="free",
            tariff=self.tariff
        )

    def test_place_status_api(self):
        """Тест API статуса мест."""
        response = self.client.get('/api/place_status/')
        self.assertEqual(response.status_code, 200)

    def test_tariffs_api(self):
        """Тест API тарифов."""
        response = self.client.get('/api/tariffs/')
        self.assertEqual(response.status_code, 200)

    def test_promotions_api(self):
        """Тест API акций."""
        response = self.client.get('/api/promotions/')
        self.assertEqual(response.status_code, 200)
