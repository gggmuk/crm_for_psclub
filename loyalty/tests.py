import json

from django.test import TestCase

from loyalty.models import Client


class ReferralTests(TestCase):
    def test_register_with_referral_gives_bonus(self):
        c = self.client.post(
            "/api/register_client/",
            data=json.dumps({"telegram_id": 200001, "name": "Alice"}),
            content_type="application/json",
        )
        self.assertEqual(c.status_code, 201)
        code = c.json()["referral_code"]

        c2 = self.client.post(
            "/api/register_client/",
            data=json.dumps({"telegram_id": 200002, "name": "Bob", "referral_code": code}),
            content_type="application/json",
        )
        self.assertEqual(c2.status_code, 201)
        alice = Client.objects.get(telegram_id=200001)
        self.assertEqual(alice.bonus_points, 100)
        bob = Client.objects.get(telegram_id=200002)
        self.assertEqual(bob.referred_by, alice)

    def test_self_referral_rejected(self):
        c = self.client.post(
            "/api/register_client/",
            data=json.dumps({"telegram_id": 200003, "name": "Self"}),
            content_type="application/json",
        )
        code = c.json()["referral_code"]
        r = self.client.post(
            "/api/apply_referral/",
            data=json.dumps({"telegram_id": 200003, "referral_code": code}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_referral_code_unique(self):
        a = Client.objects.create(telegram_id=200004, name="A")
        b = Client.objects.create(telegram_id=200005, name="B")
        self.assertNotEqual(a.referral_code, b.referral_code)
