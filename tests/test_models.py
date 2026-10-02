"""
Тесты для моделей CRM PlayStation Club.
"""
from django.test import TestCase
from crm_core.models import Place, Tariff, Promotion, Session, Booking
from loyalty.models import Client


class TariffModelTest(TestCase):
    """Тесты модели Tariff."""

    def setUp(self):
        self.tariff = Tariff.objects.create(
            name="Test Tariff",
            hourly_rate=100.0,
            description="Test description",
            is_active=True
        )

    def test_tariff_creation(self):
        """Тест создания тарифа."""
        self.assertEqual(self.tariff.name, "Test Tariff")
        self.assertEqual(self.tariff.hourly_rate, 100.0)
        self.assertTrue(self.tariff.is_active)

    def test_tariff_str(self):
        """Тест строкового представления."""
        self.assertIn("Test Tariff", str(self.tariff))


class PlaceModelTest(TestCase):
    """Тесты модели Place."""

    def setUp(self):
        self.tariff = Tariff.objects.create(
            name="VIP",
            hourly_rate=500.0
        )
        self.place = Place.objects.create(
            name="VIP Room 1",
            place_type="VIP",
            status="free",
            tariff=self.tariff
        )

    def test_place_creation(self):
        """Тест создания места."""
        self.assertEqual(self.place.name, "VIP Room 1")
        self.assertEqual(self.place.place_type, "VIP")
        self.assertEqual(self.place.status, "free")

    def test_place_tariff(self):
        """Тест связи с тарифом."""
        self.assertEqual(self.place.tariff.name, "VIP")


class PromotionModelTest(TestCase):
    """Тесты модели Promotion."""

    def setUp(self):
        self.promotion = Promotion.objects.create(
            name="Test Promotion",
            discount_percentage=10,
            description="Test promotion",
            is_active=True
        )

    def test_promotion_creation(self):
        """Тест создания акции."""
        self.assertEqual(self.promotion.name, "Test Promotion")
        self.assertEqual(self.promotion.discount_percentage, 10)
        self.assertTrue(self.promotion.is_active)


class ClientModelTest(TestCase):
    """Тесты модели Client."""

    def setUp(self):
        self.client = Client.objects.create(
            telegram_id=123456789,
            name="Test Client",
            rank="Новичок",
            bonus_points=100,
            total_hours_played=10.5
        )

    def test_client_creation(self):
        """Тест создания клиента."""
        self.assertEqual(self.client.name, "Test Client")
        self.assertEqual(self.client.telegram_id, 123456789)
        self.assertEqual(self.client.bonus_points, 100)

    def test_referral_code_auto_generated(self):
        """Тест автоматической генерации реферального кода."""
        self.assertIsNotNone(self.client.referral_code)
        self.assertEqual(len(self.client.referral_code), 8)

    def test_client_str(self):
        """Тест строкового представления."""
        self.assertIn("Test Client", str(self.client))
