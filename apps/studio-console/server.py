#!/usr/bin/env python3
"""ELP Studio Console — reverse-proxy + static UI in front of PicPeak.

Talks to the existing PicPeak container. Does not store media, passwords,
or gallery databases. Bind-mounts brands/ read-only.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public"
GALLERY = HERE.parent / "gallery"
sys.path.insert(0, str(GALLERY))
from elp_lib import BRANDS_DIR, load_brands, load_dotenv  # noqa: E402

load_dotenv(GALLERY / ".env")

LISTEN_HOST = os.environ.get("STUDIO_BIND", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("STUDIO_PORT", "3080"))
PICPEAK_ORIGIN = os.environ.get("PICPEAK_ORIGIN", "http://127.0.0.1:3000").rstrip("/")
PICPEAK_PUBLIC_ORIGIN = os.environ.get("PICPEAK_PUBLIC_ORIGIN", "http://localhost:3000").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")


def _config() -> dict:
    return {
        "picpeakPublicOrigin": PICPEAK_PUBLIC_ORIGIN,
        "adminEmailDefault": ADMIN_EMAIL,
        "proxyPrefix": "/pp",
        "brands": load_brands(),
        "layouts": [
            {"id": "grid", "label": "Grid"},
            {"id": "masonry", "label": "Masonry"},
            {"id": "carousel", "label": "Carousel"},
            {"id": "timeline", "label": "Timeline"},
            {"id": "mosaic", "label": "Mosaic"},
            {"id": "gallery-premium", "label": "Gallery Premium"},
            {"id": "gallery-story", "label": "Gallery Story"},
        ],
        "accessModes": [
            {"id": "password", "label": "Password-protected", "require_password": True},
            {"id": "unlisted", "label": "Unlisted link (no password)", "require_password": False},
        ],
        "video": {
            "accept": ".jpg,.jpeg,.png,.webp,.gif,.heic,.mp4,.m4v,.mov,.webm",
            "priority": "mp4",
            "also": ["mov", "webm", "m4v"],
            "maxVideoMb": 500,
            "maxPhotoMb": 50,
            "note": "PicPeak plays the uploaded file. Prefer H.264 MP4 for mobile + desktop. Originals are not recompressed on download when original-resolution downloads are on.",
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ELPStudioConsole/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._file(PUBLIC / "index.html", "text/html; charset=utf-8")
            return
        if path == "/config.json":
            self._send_json(200, _config())
            return
        if path.startswith("/brand-assets/"):
            self._brand_asset(path[len("/brand-assets/") :])
            return
        if path.startswith("/pp/"):
            self._proxy(parsed)
            return
        rel = path.lstrip("/")
        candidate = (PUBLIC / rel).resolve()
        if str(candidate).startswith(str(PUBLIC.resolve())) and candidate.is_file():
            ctype = {
                ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".json": "application/json",
            }.get(candidate.suffix.lower(), "application/octet-stream")
            self._file(candidate, ctype)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        self._proxy(urlparse(self.path))

    def do_PUT(self):
        self._proxy(urlparse(self.path))

    def do_PATCH(self):
        self._proxy(urlparse(self.path))

    def do_DELETE(self):
        self._proxy(urlparse(self.path))

    def do_OPTIONS(self):
        self._proxy(urlparse(self.path))

    def _file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_json(404, {"error": "Missing file"})
            return
        self._send(200, path.read_bytes(), content_type)

    def _brand_asset(self, rel: str) -> None:
        # /brand-assets/<brand_id>/...
        target = (BRANDS_DIR / rel).resolve()
        if not str(target).startswith(str(BRANDS_DIR.resolve())) or not target.is_file():
            self._send_json(404, {"error": "Unknown brand asset"})
            return
        ctype = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def _proxy(self, parsed) -> None:
        if not parsed.path.startswith("/pp/"):
            self._send_json(404, {"error": "Not a PicPeak proxy path"})
            return
        dest_path = parsed.path[len("/pp") :] or "/"
        dest = PICPEAK_ORIGIN + dest_path
        if parsed.query:
            dest += "?" + parsed.query
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {}
        for key in ("Authorization", "Content-Type", "Cookie", "Accept", "Origin"):
            val = self.headers.get(key)
            if val:
                headers[key] = val
        headers["Origin"] = PICPEAK_ORIGIN
        req = Request(dest, data=body, headers=headers, method=self.command)
        try:
            with urlopen(req, timeout=120) as resp:
                payload = resp.read()
                extra = []
                set_cookie = resp.headers.get("Set-Cookie")
                if set_cookie:
                    extra.append(("Set-Cookie", set_cookie))
                ctype = resp.headers.get("Content-Type") or "application/octet-stream"
                self._send(resp.status, payload, ctype, extra)
        except HTTPError as exc:
            payload = exc.read()
            ctype = exc.headers.get("Content-Type") if exc.headers else "application/json"
            self._send(exc.code, payload or json.dumps({"error": str(exc)}).encode(), ctype or "application/json")
        except URLError as exc:
            self._send_json(
                502,
                {
                    "error": "PicPeak is not reachable from the Studio Console.",
                    "detail": str(exc.reason),
                    "origin": PICPEAK_ORIGIN,
                },
            )


def main() -> int:
    if not PUBLIC.exists():
        print("public/ missing", file=sys.stderr)
        return 1
    httpd = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"ELP Studio Console  http://127.0.0.1:{LISTEN_PORT}")
    print(f"PicPeak proxy       {PICPEAK_ORIGIN}")
    print("Does not store galleries. Stop with Ctrl+C.")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
