"""Mock PicPeak HTTP API — proves apply helpers never delete events."""
from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elp_lib import EVENT_DEFAULT_SETTINGS, EVENT_TYPES, GENERAL_SETTINGS, BUILTIN_EVENT_TYPE_SLUGS


class MockPicPeak(BaseHTTPRequestHandler):
    store = {
        "settings": {"general_allowed_file_types": "jpg,jpeg,png,webp"},
        "events": [{"id": 99, "event_name": "Keep Me", "share_token": "abc"}],
        "event_types": [
            {"slug_prefix": "wedding", "name": "Wedding"},
            {"slug_prefix": "other", "name": "Other"},
        ],
        "deleted": [],
    }

    def log_message(self, *args):
        return

    def _json(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_POST(self):
        path = urlparse(self.path).path
        if path.endswith("/api/auth/admin/login"):
            self._json(200, {"user": {"username": "admin"}, "token": "test-token"})
            return
        if path.endswith("/api/admin/event-types"):
            item = self._body()
            self.store["event_types"].append(item)
            self._json(201, item)
            return
        self.store["deleted"].append(("POST", path))
        self._json(400, {"error": "unexpected POST"})

    def do_PUT(self):
        path = urlparse(self.path).path
        body = self._body()
        if path.endswith("/api/admin/settings/general"):
            self.store["settings"].update(body)
            self._json(200, {"success": True})
            return
        if "/css-templates/" in path:
            self._json(200, {"success": True})
            return
        self._json(404, {"error": path})

    def do_GET(self):
        path = urlparse(self.path).path
        if path.endswith("/api/admin/settings"):
            self._json(200, self.store["settings"])
            return
        if path.startswith("/api/admin/event-types"):
            self._json(200, {"eventTypes": self.store["event_types"]})
            return
        self._json(404, {"error": path})

    def do_DELETE(self):
        self.store["deleted"].append(("DELETE", self.path))
        self._json(400, {"error": "apply script must not DELETE"})


class ApplySettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MockPicPeak.store["deleted"] = []
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockPicPeak)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        spec = importlib.util.spec_from_file_location(
            "apply_platform_settings", ROOT / "scripts" / "apply-platform-settings.py"
        )
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_apply_enables_video_and_optional_email_without_deleting(self):
        api = self.mod.PicPeak(f"http://127.0.0.1:{self.port}")
        api.login("admin", "test")
        api.put_general({**GENERAL_SETTINGS, **EVENT_DEFAULT_SETTINGS})
        existing = {t["slug_prefix"] for t in api.list_event_types()}
        for item in EVENT_TYPES:
            if item["slug_prefix"] in existing or item["slug_prefix"] in BUILTIN_EVENT_TYPE_SLUGS:
                continue
            api.create_event_type(item)
        settings = api.get_settings()
        self.assertIn("mp4", settings["general_allowed_file_types"])
        self.assertIn("mov", settings["general_allowed_file_types"])
        self.assertFalse(settings["event_require_customer_email"])
        slugs = {t["slug_prefix"] for t in MockPicPeak.store["event_types"]}
        self.assertIn("maternity", slugs)
        self.assertEqual(MockPicPeak.store["events"][0]["event_name"], "Keep Me")
        self.assertEqual(MockPicPeak.store["deleted"], [])


if __name__ == "__main__":
    unittest.main()
