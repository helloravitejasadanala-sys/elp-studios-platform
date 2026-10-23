#!/usr/bin/env python3
"""Apply ELP Phase 2 PicPeak settings to an EXISTING install.

Safe by design:
  - Does not create, archive, or delete galleries
  - Does not upload, replace, or delete photos
  - Does not remove Docker volumes
  - Does not change the volume name or container data directory
  - Idempotent: missing event types are added; existing types are left in place

Usage (from apps/gallery, with .env present):

    python scripts/apply-platform-settings.py --dry-run
    python scripts/apply-platform-settings.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elp_lib import (  # noqa: E402
    BUILTIN_EVENT_TYPE_SLUGS,
    EVENT_DEFAULT_SETTINGS,
    EVENT_TYPES,
    GENERAL_SETTINGS,
    STYLES_DIR,
    load_dotenv,
)

STYLES_TO_INSTALL = (
    ("wedding-editorial", 1),
    ("modern-story", 2),
    ("cinematic-event", 3),
)


class PicPeak:
    def __init__(self, origin: str):
        self.origin = origin.rstrip("/")
        self.cookie = ""
        self.token = ""

    def _request(self, method: str, path: str, data=None, headers=None) -> tuple[int, object]:
        url = f"{self.origin}{path}"
        hdrs = {"Origin": self.origin, "Accept": "application/json"}
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                cookie = resp.headers.get("Set-Cookie")
                if cookie:
                    self.cookie = cookie.split(";", 1)[0]
                parsed = json.loads(raw) if raw else {}
                return resp.status, parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {"error": str(exc)}
            except json.JSONDecodeError:
                parsed = {"error": raw or str(exc)}
            return exc.code, parsed

    def login(self, username: str, password: str) -> dict:
        code, body = self._request(
            "POST",
            "/api/auth/admin/login",
            {"username": username, "password": password},
        )
        if code >= 400 or "user" not in body:
            raise SystemExit(f"Admin login failed (HTTP {code}): {body}")
        user = body.get("user") or {}
        if body.get("token"):
            self.token = body["token"]
        elif user.get("token"):
            self.token = user["token"]
        return body

    def get_settings(self) -> dict:
        code, body = self._request("GET", "/api/admin/settings")
        if code >= 400:
            raise SystemExit(f"GET /api/admin/settings failed (HTTP {code}): {body}")
        return body if isinstance(body, dict) else {}

    def put_general(self, payload: dict) -> tuple[int, object]:
        return self._request("PUT", "/api/admin/settings/general", payload)

    def put_css(self, slot: int, name: str, css: str) -> tuple[int, object]:
        return self._request(
            "PUT",
            f"/api/admin/css-templates/{slot}",
            {"name": name, "css_content": css, "is_enabled": True},
        )

    def list_event_types(self) -> list[dict]:
        code, body = self._request("GET", "/api/admin/event-types?includeInactive=true")
        if code >= 400:
            code, body = self._request("GET", "/api/admin/event-types")
        if code >= 400:
            print(f"  WARN event-types list HTTP {code}: {body}")
            return []
        if isinstance(body, dict):
            return body.get("eventTypes") or body.get("event_types") or []
        return body if isinstance(body, list) else []

    def create_event_type(self, item: dict) -> tuple[int, object]:
        return self._request(
            "POST",
            "/api/admin/event-types",
            {
                "name": item["name"],
                "slug_prefix": item["slug_prefix"],
                "emoji": item.get("emoji") or "",
            },
        )


def _setting(settings: dict, key: str):
    if key in settings:
        return settings[key]
    # Some installs nest values
    for nest in settings.values():
        if isinstance(nest, dict) and key in nest:
            return nest[key]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes only")
    parser.add_argument("--origin", default=os.environ.get("ORIGIN", "http://127.0.0.1:3000"))
    parser.add_argument("--skip-css", action="store_true")
    parser.add_argument("--skip-event-types", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    origin = args.origin or os.environ.get("ORIGIN", "http://127.0.0.1:3000")
    user = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        print("ADMIN_PASSWORD is not set. Copy apps/gallery/.env.example to .env first.")
        return 1

    planned = {
        "general": GENERAL_SETTINGS,
        "event_defaults": EVENT_DEFAULT_SETTINGS,
        "event_types_to_ensure": [t["slug_prefix"] for t in EVENT_TYPES],
        "css_slots": [s[1] for s in STYLES_TO_INSTALL],
    }
    print("ELP platform settings apply")
    print(f"  origin: {origin}")
    print(f"  dry_run: {args.dry_run}")
    print("  will NOT create/delete galleries or touch Docker volumes")
    print(json.dumps(planned, indent=2))
    if args.dry_run:
        return 0

    api = PicPeak(origin)
    login = api.login(user, password)
    print("logged in as", (login.get("user") or {}).get("username"))
    if login.get("mustChangePassword") or (login.get("user") or {}).get("mustChangePassword"):
        print("WARN: PicPeak is asking for an admin password change. Complete that in Admin, then re-run.")
        return 2

    before = api.get_settings()
    print("PicPeak settings readable:", sorted(k for k in before.keys() if isinstance(k, str))[:12], "...")

    general_payload = {**GENERAL_SETTINGS, **EVENT_DEFAULT_SETTINGS}
    code, body = api.put_general(general_payload)
    print(f"PUT general+event defaults HTTP {code}: {str(body)[:240]}")

    after = api.get_settings()
    allowed = str(_setting(after, "general_allowed_file_types") or "")
    print("allowed_file_types now:", allowed or "(not echoed — check Admin → Settings → General)")
    if "mp4" not in allowed.lower() and allowed:
        print("WARN: mp4 not visible in returned settings. Open Admin → Settings → General and add mp4,mov,webm.")

    if not args.skip_event_types:
        existing = api.list_event_types()
        have = {
            (t.get("slug_prefix") or t.get("slug") or "").lower()
            for t in existing
            if isinstance(t, dict)
        }
        print("existing event types:", sorted(s for s in have if s) or have)
        for item in EVENT_TYPES:
            slug = item["slug_prefix"]
            if slug in have or slug in BUILTIN_EVENT_TYPE_SLUGS:
                continue
            code, body = api.create_event_type(item)
            print(f"  event type {slug}: HTTP {code} {str(body)[:160]}")

    if not args.skip_css:
        for style_id, slot in STYLES_TO_INSTALL:
            meta_path = STYLES_DIR / style_id / "style.json"
            css_path = STYLES_DIR / style_id / "gallery.css"
            if not meta_path.exists() or not css_path.exists():
                print(f"  skip CSS {style_id}: files missing")
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            css = css_path.read_text(encoding="utf-8")
            name = meta.get("picpeak_template_name") or style_id
            code, body = api.put_css(int(meta.get("picpeak_css_slot") or slot), name, css)
            print(f"  CSS slot {slot} ({style_id}): HTTP {code} {str(body)[:160]}")

    print("\nDone. Existing galleries and the elp-picpeak-data volume were not modified.")
    print("Next: in PicPeak Admin, open an event → Upload. The picker should list MP4/MOV.")
    print("Studio Console (tabbed create / WhatsApp): http://localhost:3080 after `docker compose up -d studio-console`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
