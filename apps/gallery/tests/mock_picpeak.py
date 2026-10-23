#!/usr/bin/env python3
"""Local PicPeak stand-in for Studio Console UI tests. Does not store real media."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

EVENTS = [
    {
        "id": 7,
        "event_name": "Mini Momentz — Keep Existing Gallery",
        "customer_name": "Existing Client",
        "event_date": "2026-10-01",
        "is_draft": False,
        "slug": "existing-gallery",
        "share_token": "sharekeep",
        "welcome_message": "<!--elp-brand:mini-momentz-->Existing photos stay.",
    }
]

# Shape of an aio:stable admin JWT (unsigned fixture — not a live secret).
STABLE_ADMIN_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpZCI6MSwidXNlcm5hbWUiOiJhZG1pbiIsInR5cGUiOiJhZG1pbiIsImlzcyI6InBpY3BlYWstYXV0aCJ9."
    "test-signature-not-a-live-secret"
)
STABLE_ADMIN_USER = {
    "id": 1,
    "username": "admin",
    "email": "admin@elp.local",
    "mustChangePassword": False,
    "role": {"name": "super_admin", "displayName": "Super Admin"},
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _json(self, code, obj, extra_headers=None):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        for key, val in extra_headers or []:
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(raw)

    def _admin_token(self):
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            item = part.strip()
            if item.startswith("admin_token="):
                return item.split("=", 1)[1]
        return ""

    def _require_admin(self):
        token = self._admin_token()
        return token in {STABLE_ADMIN_JWT, "mock-token"}

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok", "mock": True})
            return
        if path.endswith("/api/auth/session"):
            token = self._admin_token()
            if not token:
                self._json(401, {"error": "No token provided"})
                return
            if token not in {STABLE_ADMIN_JWT, "mock-token"}:
                self._json(200, {"valid": False, "error": "Invalid or expired token"})
                return
            self._json(
                200,
                {
                    "valid": True,
                    "type": "admin",
                    "expiresIn": 86400,
                    "user": "admin",
                    "adminUsername": "admin",
                    "adminUser": STABLE_ADMIN_USER,
                },
            )
            return
        if path.endswith("/api/admin/css-templates"):
            self._json(
                200,
                {
                    "templates": [
                        {"id": 1, "slot_number": 1, "name": "Wedding Editorial"},
                        {"id": 2, "slot_number": 2, "name": "Modern Story"},
                        {"id": 3, "slot_number": 3, "name": "Cinematic Event"},
                    ]
                },
            )
            return
        if path.endswith("/api/admin/settings/storage/info"):
            self._json(
                200,
                {
                    "total_used": 850000000,
                    "cataloged_bytes": 720000000,
                    "disk_total": 819855818752,
                    "disk_available": 700000000000,
                    "disk_metrics_reliable": True,
                    "storage_measurement": "disk",
                    "archive_storage": 0,
                    "storage_by_event": [{"id": 7, "event_name": "Mini Momentz — Keep Existing Gallery", "size": 720000000}],
                    "storage_soft_limit": None,
                    "configured_soft_limit": None,
                    "soft_limit_configured": False,
                },
            )
            return
        if path.endswith("/api/admin/settings"):
            self._json(
                200,
                {
                    "backup_enabled": False,
                    "general_max_file_size_mb": 50,
                    "general_max_video_size_mb": 500,
                    "general_allowed_file_types": "jpg,jpeg,png,webp,mp4,mov,webm",
                },
            )
            return
        if path.endswith("/api/admin/backup/config") or path.endswith("/api/admin/backup/status"):
            self._json(200, {"backup_enabled": False, "backup_destination_type": None})
            return
        if path.startswith("/api/admin/events"):
            self._json(200, {"events": EVENTS})
            return
        if "/photos/" in path:
            self._json(
                200,
                {
                    "photos": [
                        {"id": 1, "filename": "demo.jpg", "size_bytes": 1200000, "mime_type": "image/jpeg", "created_at": "2026-10-20T10:00:00Z"},
                        {"id": 2, "filename": "clip.mp4", "size_bytes": 8800000, "mime_type": "video/mp4", "created_at": "2026-10-21T10:00:00Z"},
                    ]
                },
            )
            return
        self._json(404, {"error": path})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path.endswith("/api/auth/admin/login"):
            username = (body.get("username") or "").strip()
            password = body.get("password") or ""
            if not username or not password:
                self._json(400, {"error": "Username and password required"})
                return
            if username != "admin" or password != "ElpDemo2026!":
                self._json(401, {"error": "Invalid credentials"})
                return
            # aio:stable: JWT is the admin_token cookie only — no token field in JSON.
            self._json(
                200,
                {"user": STABLE_ADMIN_USER},
                extra_headers=[
                    (
                        "Set-Cookie",
                        f"admin_token={STABLE_ADMIN_JWT}; Max-Age=86400; Path=/; HttpOnly; Secure; SameSite=Lax; Domain=picpeak",
                    )
                ],
            )
            return
        if path.endswith("/api/auth/logout"):
            self._json(
                200,
                {"success": True},
                extra_headers=[
                    (
                        "Set-Cookie",
                        "admin_token=; Path=/; HttpOnly; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT",
                    )
                ],
            )
            return
        if path.endswith("/api/admin/events"):
            if "customer_email" in body and body["customer_email"] in ("", None):
                self._json(400, {"error": "empty email should have been omitted"})
                return
            ev = {
                "id": 101,
                "event_name": body.get("event_name"),
                "customer_name": body.get("customer_name"),
                "customer_email": body.get("customer_email"),
                "customer_phone": body.get("customer_phone"),
                "welcome_message": body.get("welcome_message"),
                "is_draft": True,
                "slug": "new-no-email",
                "share_token": "newshare",
                "event_date": body.get("event_date"),
            }
            EVENTS.append(ev)
            self._json(201, ev)
            return
        if path.endswith("/logo") or path.endswith("/upload") or path.endswith("/publish"):
            self._json(200, {"success": True, "count": 1, "photo_ids": [2]})
            return
        self._json(200, {"ok": True})

    def do_PUT(self):
        self._json(200, {"success": True})


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("127.0.0.1", 3000), H)
    print("mock PicPeak on http://127.0.0.1:3000")
    httpd.serve_forever()
