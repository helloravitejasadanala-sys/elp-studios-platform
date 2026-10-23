import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elp_lib import (
    event_create_payload,
    infer_brand_from_event,
    load_brands,
    parse_elp_meta,
    share_message,
    whatsapp_url,
    compose_welcome,
)


class BrandCatalogTests(unittest.TestCase):
    def test_three_brands_present(self):
        ids = [b["id"] for b in load_brands()]
        self.assertEqual(ids, ["mini-momentz", "katha-films", "tattva-weddings"])

    def test_mini_and_tattva_use_genuine_logos(self):
        brands = {b["id"]: b for b in load_brands()}
        self.assertTrue(brands["mini-momentz"]["has_genuine_logo"])
        self.assertTrue(brands["tattva-weddings"]["has_genuine_logo"])
        self.assertFalse(brands["katha-films"]["has_genuine_logo"])

    def test_whatsapp_uses_brand_name(self):
        mini = next(b for b in load_brands() if b["id"] == "mini-momentz")
        msg = share_message(mini, "http://localhost:3000/gallery/demo/abc")
        self.assertIn("Mini Momentz", msg)
        self.assertIn("http://localhost:3000/gallery/demo/abc", msg)
        url = whatsapp_url(msg, "+44 7700 900123")
        self.assertTrue(url.startswith("https://wa.me/447700900123?text="))

    def test_welcome_meta_roundtrip(self):
        raw = compose_welcome("tattva-weddings", "Hello family", "full-day")
        parsed = parse_elp_meta(raw)
        self.assertEqual(parsed["brand_id"], "tattva-weddings")
        self.assertEqual(parsed["duration"], "full-day")
        self.assertEqual(parsed["welcome_visible"], "Hello family")

    def test_infer_brand_from_welcome(self):
        ev = {"welcome_message": compose_welcome("katha-films", "Hi", None), "event_name": "X"}
        self.assertEqual(infer_brand_from_event(ev), "katha-films")

    def test_create_payload_omits_empty_email(self):
        payload = event_create_payload(
            brand_id="mini-momentz",
            event_name="Seemantham",
            event_type="maternity",
            event_date="2026-10-12",
            client_name="Divya",
            client_email="",
            client_phone="+447700900123",
            admin_email="admin@elp.local",
            welcome="Hello",
            duration="partial-day",
            require_password=True,
            password="GuestDemo1",
            expiration_days=180,
            allow_downloads=True,
            allow_original=True,
            watermark_downloads=False,
            feedback_enabled=True,
            allow_favorites=True,
            allow_likes=True,
            allow_comments=True,
            allow_user_uploads=False,
            css_template_id=2,
        )
        self.assertNotIn("customer_email", payload)
        self.assertEqual(payload["customer_phone"], "+447700900123")
        self.assertIn("elp-brand:mini-momentz", payload["welcome_message"])
        self.assertTrue(payload["require_password"])


if __name__ == "__main__":
    unittest.main()
