from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm_core.models import Booking, Place, Session, Tariff
from crm_core.services import (
    auto_close_expired_bookings,
    auto_close_expired_sessions,
    start_session,
    stop_session,
)
from loyalty.models import Client


class SessionFlowTests(TestCase):
    def setUp(self):
        self.tariff = Tariff.objects.create(name="Test", hourly_rate=200)
        self.place = Place.objects.create(name="PC-1", place_type="Basic", status="free", tariff=self.tariff)
        self.client = Client.objects.create(telegram_id=100001, name="Tester")

    def test_start_stop_session_charges_ceiling(self):
        session = start_session(self.client, self.place)
        self.place.refresh_from_db()
        self.assertEqual(self.place.status, "occupied")
        result = stop_session(session.id)
        # ceil(<1 мин) = 1 час * 200
        self.assertEqual(float(result["cost"]), 200.0)
        self.assertEqual(result["bonus_points_added"], 2)  # 1% от 200

    def test_cannot_start_on_occupied(self):
        start_session(self.client, self.place)
        with self.assertRaises(ValueError):
            start_session(self.client, self.place)

    def test_auto_close_expired(self):
        session = start_session(self.client, self.place, duration_minutes=60)
        session.scheduled_end_time = timezone.now() - timedelta(minutes=1)
        session.save(update_fields=["scheduled_end_time"])
        closed = auto_close_expired_sessions()
        self.assertEqual(closed, 1)
        session.refresh_from_db()
        self.assertEqual(session.status, "completed")


class BookingOverlapTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(name="PC-2", place_type="Basic", status="free")
        self.client = Client.objects.create(telegram_id=100002, name="Booker")

    def test_expired_pending_autocancel(self):
        now = timezone.now()
        b = Booking.objects.create(
            client=self.client, place=self.place,
            start_time=now - timedelta(hours=3), end_time=now - timedelta(hours=2),
            status="pending",
        )
        auto_close_expired_bookings()
        b.refresh_from_db()
        self.assertEqual(b.status, "canceled")

    def test_expired_confirmed_autocomplete(self):
        now = timezone.now()
        b = Booking.objects.create(
            client=self.client, place=self.place,
            start_time=now - timedelta(hours=3), end_time=now - timedelta(hours=2),
            status="confirmed",
        )
        auto_close_expired_bookings()
        b.refresh_from_db()
        self.assertEqual(b.status, "completed")
