"""Studio Console auth against aio:stable login (cookie JWT, no JSON token)."""
from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "gallery"))
sys.path.insert(0, str(ROOT / "apps" / "studio-console"))
sys.path.insert(0, str(ROOT / "apps" / "gallery" / "tests"))

from elp_lib import (  # noqa: E402
    admin_token_from_set_cookie,
    rewrite_picpeak_cookie_for_proxy,
    session_from_picpeak_login,
)
from mock_picpeak import STABLE_ADMIN_JWT  # noqa: E402

# Documented PicPeak aio:stable login JSON — token is NOT in the body.
STABLE_LOGIN_BODY = {
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@elp.local",
        "mustChangePassword": False,
        "role": {"name": "super_admin", "displayName": "Super Admin"},
    }
}
STABLE_SET_COOKIE = (
    f"admin_token={STABLE_ADMIN_JWT}; Max-Age=86400; Path=/; HttpOnly; Secure; SameSite=Lax; Domain=picpeak"
)


class PicPeakLoginShapeTests(unittest.TestCase):
    def test_stable_body_has_user_and_no_token_field(self):
        self.assertIn("user", STABLE_LOGIN_BODY)
        self.assertNotIn("token", STABLE_LOGIN_BODY)
        self.assertNotIn("token", STABLE_LOGIN_BODY["user"])

    def test_session_from_cookie_not_json_token(self):
        parsed = session_from_picpeak_login(STABLE_LOGIN_BODY, [STABLE_SET_COOKIE])
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["user"]["username"], "admin")
        self.assertEqual(parsed["token"], STABLE_ADMIN_JWT)
        self.assertTrue(parsed["cookie_session"])

    def test_user_without_captured_cookie_is_still_success_body(self):
        parsed = session_from_picpeak_login(STABLE_LOGIN_BODY, [])
        self.assertTrue(parsed["ok"])
        self.assertIsNone(parsed["token"])
        self.assertFalse(parsed["cookie_session"])

    def test_empty_or_error_body_is_not_a_session(self):
        self.assertFalse(session_from_picpeak_login({}, [])["ok"])
        self.assertFalse(session_from_picpeak_login({"error": "Invalid credentials"}, [])["ok"])
        self.assertEqual(session_from_picpeak_login({"mfaRequired": True, "mfaToken": "x"}, [])["reason"], "mfa")

    def test_does_not_invent_a_token(self):
        parsed = session_from_picpeak_login(STABLE_LOGIN_BODY, [])
        self.assertIsNone(parsed["token"])

    def test_rewrite_cookie_drops_domain_and_secure_keeps_httponly(self):
        out = rewrite_picpeak_cookie_for_proxy(STABLE_SET_COOKIE)
        self.assertTrue(out.startswith("admin_token="))
        self.assertIn("HttpOnly", out)
        self.assertIn("Path=/", out)
        self.assertNotIn("Domain=", out)
        self.assertNotIn("Secure", out)
        self.assertEqual(admin_token_from_set_cookie([out]), STABLE_ADMIN_JWT)


class StudioProxyAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server as studio
        from mock_picpeak import H as MockPicPeak

        cls.studio = studio
        cls.mock = studio.ThreadingHTTPServer(("127.0.0.1", 0), MockPicPeak)
        cls.mock_thread = threading.Thread(target=cls.mock.serve_forever, daemon=True)
        cls.mock_thread.start()
        cls.prev_origin = studio.PICPEAK_ORIGIN
        studio.PICPEAK_ORIGIN = f"http://127.0.0.1:{cls.mock.server_address[1]}"
        cls.httpd = studio.ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.studio.PICPEAK_ORIGIN = cls.prev_origin
        cls.httpd.shutdown()
        cls.mock.shutdown()

    def _json(self, method, path, data=None, cookie=None, token=None):
        headers = {"Accept": "application/json"}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        if cookie:
            headers["Cookie"] = cookie
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as resp:
                raw = resp.read().decode()
                cookies = resp.headers.get_all("Set-Cookie") or []
                return resp.status, json.loads(raw) if raw else {}, cookies
        except HTTPError as exc:
            raw = exc.read().decode()
            cookies = exc.headers.get_all("Set-Cookie") if exc.headers else []
            return exc.code, json.loads(raw) if raw else {}, cookies or []

    def test_login_forwards_admin_token_cookie_and_omits_json_token(self):
        code, body, cookies = self._json(
            "POST",
            "/pp/api/auth/admin/login",
            {"username": "admin", "password": "ElpDemo2026!"},
        )
        self.assertEqual(code, 200)
        self.assertIn("user", body)
        self.assertEqual(body["user"]["username"], "admin")
        self.assertNotIn("token", body)
        self.assertTrue(any("admin_token=" in c for c in cookies), cookies)
        joined = " ".join(cookies)
        self.assertIn("HttpOnly", joined)
        self.assertNotIn("Domain=picpeak", joined)
        self.assertNotRegex(joined, r"(^|[; ])Secure([; ]|$)")
        token = admin_token_from_set_cookie(cookies)
        self.assertEqual(token, STABLE_ADMIN_JWT)

        code, session, _ = self._json("GET", "/pp/api/auth/session", cookie=f"admin_token={token}")
        self.assertEqual(code, 200)
        self.assertTrue(session.get("valid"))
        self.assertEqual(session.get("type"), "admin")
        self.assertEqual(session.get("adminUsername"), "admin")

    def test_wrong_password_has_no_session_cookie(self):
        code, body, cookies = self._json(
            "POST",
            "/pp/api/auth/admin/login",
            {"username": "admin", "password": "not-the-password"},
        )
        self.assertEqual(code, 401)
        self.assertFalse(session_from_picpeak_login(body, cookies)["ok"])
        self.assertFalse(any("admin_token=" in c and STABLE_ADMIN_JWT in c for c in cookies))

    def test_logout_clears_admin_token_and_session(self):
        _code, _body, cookies = self._json(
            "POST",
            "/pp/api/auth/admin/login",
            {"username": "admin", "password": "ElpDemo2026!"},
        )
        token = admin_token_from_set_cookie(cookies)
        self.assertTrue(token)
        code, _logout, clear = self._json(
            "POST", "/pp/api/auth/logout", cookie=f"admin_token={token}"
        )
        self.assertEqual(code, 200)
        self.assertTrue(any(c.startswith("admin_token=") for c in clear), clear)
        cleared = admin_token_from_set_cookie(clear)
        self.assertIsNone(cleared)
        code, session, _ = self._json("GET", "/pp/api/auth/session")
        self.assertEqual(code, 401)
        self.assertEqual(session.get("error"), "No token provided")

    def test_session_without_credentials_is_unauthorized(self):
        code, body, _ = self._json("GET", "/pp/api/auth/session")
        self.assertEqual(code, 401)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
