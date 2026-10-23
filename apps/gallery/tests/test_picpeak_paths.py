"""Regression: Studio Console must never send /api/api/... to PicPeak."""
from __future__ import annotations

import json
import subprocess
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
    PICPEAK_LOGIN_PATH,
    PICPEAK_LOGOUT_PATH,
    PICPEAK_SESSION_PATH,
    collapse_duplicate_api_prefix,
    join_picpeak_url,
    normalize_picpeak_origin,
    normalize_picpeak_path,
    picpeak_proxy_url,
)

AUTH_PATHS = (PICPEAK_LOGIN_PATH, PICPEAK_SESSION_PATH, PICPEAK_LOGOUT_PATH)
APP_JS = ROOT / "apps" / "studio-console" / "public" / "app.js"


class JoinPicPeakUrlTests(unittest.TestCase):
    def test_host_only_origin_keeps_single_api(self):
        for path in AUTH_PATHS:
            url = join_picpeak_url("http://picpeak:3000", path)
            self.assertEqual(url, "http://picpeak:3000" + path)
            self.assertNotIn("/api/api", url)

    def test_origin_that_already_includes_api_is_not_doubled(self):
        for origin in (
            "http://picpeak:3000/api",
            "http://picpeak:3000/api/",
            "http://127.0.0.1:3000/api",
        ):
            for path in AUTH_PATHS:
                url = join_picpeak_url(origin, path)
                host = normalize_picpeak_origin(origin)
                self.assertEqual(url, host + path, (origin, path, url))
                self.assertNotIn("/api/api", url)

    def test_proxy_prefix_and_doubled_api_collapse(self):
        cases = [
            "/pp/api/auth/admin/login",
            "/pp/api/api/auth/admin/login",
            "/api/api/auth/admin/login",
            "/pp/pp/api/auth/admin/login",
            "http://ignored/pp/api/api/auth/admin/login",
        ]
        for path in cases:
            url = join_picpeak_url("http://picpeak:3000/api", path)
            self.assertEqual(url, "http://picpeak:3000" + PICPEAK_LOGIN_PATH, path)
            self.assertNotIn("/api/api", url)

    def test_session_and_logout_single_api(self):
        self.assertEqual(
            join_picpeak_url("http://picpeak:3000/api", "/pp/api/api/auth/session"),
            "http://picpeak:3000/api/auth/session",
        )
        self.assertEqual(
            join_picpeak_url("http://picpeak:3000", "/pp/api/auth/logout"),
            "http://picpeak:3000/api/auth/logout",
        )

    def test_naive_concat_would_double_but_join_does_not(self):
        origin = "http://picpeak:3000/api"
        path = PICPEAK_LOGIN_PATH
        naive = origin.rstrip("/") + path
        self.assertEqual(naive, "http://picpeak:3000/api/api/auth/admin/login")
        self.assertEqual(join_picpeak_url(origin, path), "http://picpeak:3000/api/auth/admin/login")

    def test_query_string_preserved(self):
        url = join_picpeak_url("http://picpeak:3000/api", "/pp/api/admin/events", "page=1&limit=100")
        self.assertEqual(url, "http://picpeak:3000/api/admin/events?page=1&limit=100")
        self.assertNotIn("/api/api", url)

    def test_normalize_helpers(self):
        self.assertEqual(normalize_picpeak_origin("http://picpeak:3000/api"), "http://picpeak:3000")
        self.assertEqual(normalize_picpeak_path("/pp/api/api/auth/session"), PICPEAK_SESSION_PATH)
        self.assertEqual(collapse_duplicate_api_prefix("/api/api/api/auth/logout"), PICPEAK_LOGOUT_PATH)
        self.assertEqual(picpeak_proxy_url("/api/api/auth/admin/login"), "/pp/api/auth/admin/login")
        self.assertEqual(picpeak_proxy_url("/pp/api/auth/logout"), "/pp/api/auth/logout")

    def test_fuzz_never_emits_api_api(self):
        origins = [
            "http://picpeak:3000",
            "http://picpeak:3000/",
            "http://picpeak:3000/api",
            "http://picpeak:3000/api/",
            "picpeak:3000/api",
        ]
        paths = [
            PICPEAK_LOGIN_PATH,
            "/pp" + PICPEAK_LOGIN_PATH,
            "/pp/api/api/auth/admin/login",
            "/api/api/auth/session",
            "/pp/api/auth/logout",
            "/pp/api/api/auth/logout",
            "/api/admin/settings/storage/info",
            "/pp/api/api/admin/events?page=1",
        ]
        for origin in origins:
            for path in paths:
                url = join_picpeak_url(origin, path)
                self.assertNotIn("/api/api", url, (origin, path, url))
                self.assertTrue(url.startswith("http://"), url)
                proxy = picpeak_proxy_url(path)
                self.assertNotIn("/api/api", proxy, (path, proxy))
                self.assertTrue(proxy.startswith("/pp/"), proxy)


class StudioProxyExactPathTests(unittest.TestCase):
    """Live proxy must hit exact PicPeak routes even when origin already has /api."""

    @classmethod
    def setUpClass(cls):
        import server as studio
        from mock_picpeak import H as MockPicPeak

        cls.studio = studio
        cls.MockPicPeak = MockPicPeak
        cls.mock = studio.ThreadingHTTPServer(("127.0.0.1", 0), MockPicPeak)
        cls.mock_thread = threading.Thread(target=cls.mock.serve_forever, daemon=True)
        cls.mock_thread.start()
        cls.prev_origin = studio.PICPEAK_ORIGIN
        cls.mock_port = cls.mock.server_address[1]
        # The live bug: PICPEAK_ORIGIN ended in /api, then path also started with /api.
        studio.PICPEAK_ORIGIN = f"http://127.0.0.1:{cls.mock_port}/api"
        cls.httpd = studio.ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.studio.PICPEAK_ORIGIN = cls.prev_origin
        cls.httpd.shutdown()
        cls.mock.shutdown()

    def setUp(self):
        self.MockPicPeak.seen = []

    def _json(self, method, path, data=None):
        headers = {"Accept": "application/json"}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        req = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode()
            return exc.code, json.loads(raw) if raw else {}

    def test_login_hits_exactly_api_auth_admin_login(self):
        code, body = self._json(
            "POST",
            "/pp/api/auth/admin/login",
            {"username": "admin", "password": "ElpDemo2026!"},
        )
        self.assertEqual(code, 200, body)
        self.assertEqual(body.get("user", {}).get("username"), "admin")
        self.assertIn(("POST", PICPEAK_LOGIN_PATH), self.MockPicPeak.seen)
        self.assertNotIn(("POST", "/api/api/auth/admin/login"), self.MockPicPeak.seen)
        for _method, path in self.MockPicPeak.seen:
            self.assertNotIn("/api/api", path)

    def test_doubled_client_login_path_is_collapsed(self):
        code, body = self._json(
            "POST",
            "/pp/api/api/auth/admin/login",
            {"username": "admin", "password": "ElpDemo2026!"},
        )
        self.assertEqual(code, 200, body)
        self.assertEqual(self.MockPicPeak.seen[-1], ("POST", PICPEAK_LOGIN_PATH))

    def test_session_hits_exactly_api_auth_session(self):
        code, _body = self._json("GET", "/pp/api/auth/session")
        self.assertEqual(code, 401)
        self.assertIn(("GET", PICPEAK_SESSION_PATH), self.MockPicPeak.seen)
        self.assertNotIn(("GET", "/api/api/auth/session"), self.MockPicPeak.seen)

    def test_logout_hits_exactly_api_auth_logout(self):
        code, body = self._json("POST", "/pp/api/auth/logout")
        self.assertEqual(code, 200, body)
        self.assertIn(("POST", PICPEAK_LOGOUT_PATH), self.MockPicPeak.seen)
        self.assertNotIn(("POST", "/api/api/auth/logout"), self.MockPicPeak.seen)

    def test_mock_rejects_raw_doubled_api_if_join_is_bypassed(self):
        req = Request(
            f"http://127.0.0.1:{self.mock_port}/api/api/auth/admin/login",
            data=b'{"username":"admin","password":"ElpDemo2026!"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 404)
        detail = json.loads(ctx.exception.read().decode())
        self.assertEqual(detail.get("path"), "/api/api/auth/admin/login")


class AppJsPathJoinTests(unittest.TestCase):
    def test_api_helper_uses_picpeak_proxy_url(self):
        src = APP_JS.read_text(encoding="utf-8")
        self.assertIn("function picpeakProxyUrl(", src)
        self.assertIn("fetch(picpeakProxyUrl(path)", src)
        self.assertNotIn('fetch("/pp" + path', src)
        self.assertIn("p.startsWith(\"/api/api\")", src)
        self.assertIn("function describeApiError(", src)
        self.assertIn("err.status === 429", src)

    def test_js_picpeak_proxy_url_collapses_api_api(self):
        src = APP_JS.read_text(encoding="utf-8")
        start = src.find("function picpeakProxyUrl")
        self.assertGreaterEqual(start, 0, "picpeakProxyUrl not found in app.js")
        end = src.find("\nfunction ", start)
        self.assertGreater(end, start, "could not bound picpeakProxyUrl")
        js_fn = src[start:end]
        probe = (
            js_fn
            + """
            const state = { config: { proxyPrefix: '/pp' } };
            const cases = [
              ['/api/auth/admin/login', '/pp/api/auth/admin/login'],
              ['/api/api/auth/admin/login', '/pp/api/auth/admin/login'],
              ['/pp/api/auth/admin/login', '/pp/api/auth/admin/login'],
              ['/pp/api/api/auth/session', '/pp/api/auth/session'],
              ['/api/auth/logout', '/pp/api/auth/logout'],
              ['/api/api/auth/logout', '/pp/api/auth/logout'],
            ];
            for (const [input, expected] of cases) {
              const got = picpeakProxyUrl(input);
              if (got !== expected || got.includes('/api/api')) {
                throw new Error(input + ' -> ' + got + ' expected ' + expected);
              }
            }
            console.log('ok');
            """
        )
        try:
            proc = subprocess.run(
                ["node", "-e", probe],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            self.skipTest("node is not installed")
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
