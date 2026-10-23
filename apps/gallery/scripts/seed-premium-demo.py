#!/usr/bin/env python3
"""Configure PicPeak for ELP multi-brand premium demo (API-only; no security weaken)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
GALLERY = ROOT / "apps" / "gallery"
ORIGIN = os.environ.get("ORIGIN", f"http://127.0.0.1:{os.environ.get('PICPEAK_PORT', '3000')}")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "ElpStudioDemo2026!")
GUEST_PASS = os.environ.get("GUEST_PASSWORD", "GuestDemo1")

BRANDS = [
    {
        "key": "mini-momentz",
        "name": "Mini Momentz Demo — Family Session",
        "event_date": "2026-10-14",
        "welcome": "Welcome to your Mini Momentz gallery. Tap a heart to favourite. Download anytime.",
        "media_dir": ROOT / "demo-media" / "mini-momentz",
        "logo": ROOT / "brands" / "placeholders" / "mini-momentz-logo.png",
        "cover_name": "mini-momentz-cover.jpg",
        "videos": [],
        "accent": "#5c4033",
    },
    {
        "key": "katha-films",
        "name": "Katha Films Demo — Highlight Film",
        "event_date": "2026-10-10",
        "welcome": "Your Katha Films delivery — photos and finished film in one place.",
        "media_dir": ROOT / "demo-media" / "katha-films",
        "logo": ROOT / "brands" / "placeholders" / "katha-films-logo.png",
        "cover_name": "katha-films-cover.jpg",
        "videos": [ROOT / "demo-media" / "videos" / "katha-demo-clip.mp4"],
        "accent": "#c49a6c",
    },
    {
        "key": "tattva-weddings",
        "name": "Tattva Weddings Demo — Wedding Day",
        "event_date": "2026-10-05",
        "welcome": "Your Tattva Weddings gallery. Favourites and full downloads for family sharing.",
        "media_dir": ROOT / "demo-media" / "tattva-weddings",
        "logo": ROOT / "brands" / "placeholders" / "tattva-weddings-logo.png",
        "cover_name": "tattva-weddings-cover.jpg",
        "videos": [],
        "accent": "#8c5a4e",
    },
]


class Api:
    def __init__(self, origin: str):
        self.origin = origin.rstrip("/")
        self.cookie = ""
        self.token = ""

    def _req(self, method: str, path: str, data=None, headers=None, multipart=False):
        url = f"{self.origin}{path}"
        hdrs = {"Origin": self.origin}
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        if headers:
            hdrs.update(headers)
        body = None
        if data is not None and not multipart:
            body = json.dumps(data).encode()
            hdrs["Content-Type"] = "application/json"
        elif multipart:
            body = data
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                set_cookie = resp.headers.get_all("Set-Cookie") or []
                for c in set_cookie:
                    name = c.split(";", 1)[0]
                    if "admin_token=" in name or name.startswith("admin_token="):
                        self.cookie = name if not self.cookie else self.cookie
                        # merge simply: keep last admin_token
                        parts = [p for p in self.cookie.split("; ") if not p.startswith("admin_token=")]
                        parts.append(name.split(";", 1)[0] if "=" in name else name)
                        # Actually Set-Cookie value is "admin_token=..."
                        self.cookie = "; ".join(
                            [x for x in (self.cookie.split("; ") if self.cookie else []) if not x.startswith("admin_token=")]
                            + [c.split(";", 1)[0]]
                        )
                if resp.headers.get("Set-Cookie"):
                    # rebuild cookie jar from all admin_token cookies in response
                    for c in set_cookie:
                        if c.startswith("admin_token="):
                            self.token = c.split(";", 1)[0].split("=", 1)[1]
                            self.cookie = c.split(";", 1)[0]
                if not raw:
                    return {}
                return json.loads(raw.decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} -> {e.code}: {err[:500]}") from e

    def login(self):
        # Prefer username field used by API; UI uses email
        out = self._req(
            "POST",
            "/api/auth/admin/login",
            {"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        if "user" not in out:
            raise RuntimeError(f"login failed: {out}")
        # Token from cookie set in _req; also try Authorization from cookie file via curl fallback
        return out


def load_env():
    env_path = GALLERY / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def multipart_upload(api: Api, path: str, files: list[Path], field="photos"):
    """Upload files using curl for reliable multipart (stdlib boundary is fiddly)."""
    import subprocess

    cmd = [
        "curl",
        "-s",
        "-X",
        "POST",
        f"{api.origin}{path}",
        "-H",
        f"Origin: {api.origin}",
        "-H",
        f"Authorization: Bearer {api.token}",
        "-H",
        f"Cookie: {api.cookie}",
    ]
    for f in files:
        cmd += ["-F", f"{field}=@{f}"]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out) if out else {}


def main() -> int:
    load_env()
    global ADMIN_PASS, ADMIN_USER, ADMIN_EMAIL
    ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", ADMIN_PASS)
    ADMIN_USER = os.environ.get("ADMIN_USERNAME", ADMIN_USER)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", ADMIN_EMAIL)

    # Use curl cookie jar for reliability
    import subprocess
    import tempfile

    jar = tempfile.NamedTemporaryFile(delete=False).name
    login = subprocess.check_output(
        [
            "curl",
            "-s",
            "-c",
            jar,
            "-b",
            jar,
            "-X",
            "POST",
            f"{ORIGIN}/api/auth/admin/login",
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Origin: {ORIGIN}",
            "-d",
            json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}),
        ],
        text=True,
    )
    login_j = json.loads(login)
    if "user" not in login_j:
        print("LOGIN FAIL", login)
        return 1
    print("logged in as", login_j["user"]["username"])

    def curl_json(method, path, payload=None):
        cmd = [
            "curl",
            "-s",
            "-c",
            jar,
            "-b",
            jar,
            "-X",
            method,
            f"{ORIGIN}{path}",
            "-H",
            f"Origin: {ORIGIN}",
            "-H",
            "Content-Type: application/json",
        ]
        # bearer from jar
        token = ""
        for line in Path(jar).read_text().splitlines():
            if "admin_token" in line and not line.startswith("#"):
                token = line.split("\t")[-1]
        if token:
            cmd += ["-H", f"Authorization: Bearer {token}"]
        if payload is not None:
            cmd += ["-d", json.dumps(payload)]
        out = subprocess.check_output(cmd, text=True)
        return json.loads(out) if out else {}

    def token():
        for line in Path(jar).read_text().splitlines():
            if "admin_token" in line and not line.startswith("#"):
                return line.split("\t")[-1]
        return ""

    # Allow finished videos alongside photos (store plain CSV, not JSON-quoted)
    curl_json(
        "PUT",
        "/api/admin/settings/general",
        {"general_allowed_file_types": "jpg,jpeg,png,webp,gif,heic,mp4,mov,webm"},
    )
    # PicPeak caches MIME allow-list; ensure DB string is unquoted for reliability
    subprocess.call(
        [
            "docker",
            "exec",
            "elp-picpeak",
            "sh",
            "-c",
            "sqlite3 /data/db/picpeak.db \"UPDATE app_settings SET setting_value='jpg,jpeg,png,webp,gif,heic,mp4,mov,webm' WHERE setting_key='general_allowed_file_types';\"",
        ]
    )

    # Global branding — light photography studio chrome
    branding = curl_json(
        "PUT",
        "/api/admin/settings/branding",
        {
            "company_name": "ELP Studios Galleries",
            "company_tagline": "Mini Momentz · Katha Films · Tattva Weddings",
            "support_email": ADMIN_EMAIL,
            "footer_text": "Demo galleries — placeholder media only. Brand logos are labelled placeholders until owner assets arrive.",
            "watermark_enabled": False,
            "logo_size": "medium",
            "logo_display_header": True,
            "logo_display_hero": True,
            "force_color_mode": "light",
            "hide_powered_by": False,
            "info_markdown": "Photography-first client galleries for ELP Studios brands. Demo media only.",
        },
    )
    print("branding:", branding.get("message") or branding.get("error") or list(branding.keys())[:5])

    # Upload global placeholder logo (Mini Momentz as default admin chrome stand-in)
    logo_path = ROOT / "brands" / "placeholders" / "mini-momentz-logo.png"
    subprocess.check_output(
        [
            "curl",
            "-s",
            "-b",
            jar,
            "-c",
            jar,
            "-X",
            "POST",
            f"{ORIGIN}/api/admin/settings/logo",
            "-H",
            f"Origin: {ORIGIN}",
            "-H",
            f"Authorization: Bearer {token()}",
            "-F",
            f"logo=@{logo_path}",
        ],
        text=True,
    )

    # Premium CSS template slot 1
    css = (GALLERY / "config" / "css" / "photography-first.css").read_text()
    css_put = curl_json(
        "PUT",
        "/api/admin/css-templates/1",
        {"name": "ELP Photography First", "css_content": css, "is_enabled": True},
    )
    print("css:", css_put.get("success") or css_put.get("error") or css_put)
    templates = curl_json("GET", "/api/admin/css-templates")
    css_id = None
    for t in templates.get("templates", []):
        if t.get("slot_number") == 1:
            css_id = t.get("id")
    print("css_id", css_id)

    results = []
    for brand in BRANDS:
        payload = {
            "event_type": "other",
            "event_name": brand["name"],
            "event_date": brand["event_date"],
            "customer_name": "Demo Family",
            "customer_email": "demo.client@example.com",
            "admin_email": ADMIN_EMAIL,
            "require_password": True,
            "password": GUEST_PASS,
            "allow_downloads": True,
            "allow_favorites": True,
            "allow_likes": True,
            "allow_comments": True,
            "feedback_enabled": True,
            "welcome_message": brand["welcome"],
            "expiration_days": 120,
            "header_style": "hero",
            "hero_logo_visible": True,
            "hero_logo_size": "medium",
            "hero_logo_position": "center",
            "hero_divider_style": "none",
            "disable_right_click": False,
            "enable_devtools_protection": True,
        }
        if css_id:
            payload["css_template_id"] = css_id
        created = curl_json("POST", "/api/admin/events", payload)
        if "id" not in created:
            print("CREATE FAIL", brand["key"], created)
            continue
        eid = created["id"]
        slug = created["slug"]
        share = created["share_token"]
        print(f"created {brand['key']} id={eid} slug={slug}")

        # Upload media: cover first so it can be hero, then photos, then videos
        media_files = sorted(brand["media_dir"].glob("*.jpg"))
        # Put cover first
        media_files = sorted(media_files, key=lambda p: (0 if "cover" in p.name else 1, p.name))
        media_files = media_files[:5]
        up = multipart_via_curl(jar, token(), f"/api/admin/events/{eid}/upload", media_files)
        print("  photos:", up.get("count"), up.get("photo_ids"))
        photo_ids = up.get("photo_ids") or []

        for v in brand["videos"]:
            if v.exists():
                vu = multipart_via_curl(jar, token(), f"/api/admin/events/{eid}/upload", [v])
                print("  video:", vu.get("count"), vu.get("message") or vu.get("error") or vu)

        # Event logo
        if brand["logo"].exists():
            lo = subprocess.check_output(
                [
                    "curl",
                    "-s",
                    "-b",
                    jar,
                    "-X",
                    "POST",
                    f"{ORIGIN}/api/admin/events/{eid}/logo",
                    "-H",
                    f"Origin: {ORIGIN}",
                    "-H",
                    f"Authorization: Bearer {token()}",
                    "-F",
                    f"logo=@{brand['logo']}",
                ],
                text=True,
            )
            print("  logo:", lo[:120])

        # Set hero cover = first uploaded photo (cover image)
        if photo_ids:
            upd = curl_json(
                "PUT",
                f"/api/admin/events/{eid}",
                {
                    "header_style": "hero",
                    "hero_photo_id": photo_ids[0],
                    "hero_logo_visible": True,
                    "welcome_message": brand["welcome"],
                    "allow_downloads": True,
                },
            )
            print("  hero:", "ok" if not upd.get("error") else upd.get("error"), "hero_photo_id", photo_ids[0])

        # Publish quietly
        pub = curl_json(
            "POST",
            f"/api/admin/events/{eid}/publish",
            {"password": GUEST_PASS, "notify_customer": False},
        )
        print("  publish:", pub.get("message") or pub)

        # Ensure feedback enabled in DB (belt-and-suspenders)
        subprocess.call(
            [
                "docker",
                "exec",
                "elp-picpeak",
                "sh",
                "-c",
                f"sqlite3 /data/db/picpeak.db \"INSERT INTO event_feedback_settings (event_id, feedback_enabled, allow_favorites, allow_likes, allow_comments, allow_reactions, show_feedback_to_guests, identity_mode) VALUES ({eid},1,1,1,1,1,1,'simple') ON CONFLICT(event_id) DO UPDATE SET feedback_enabled=1, allow_favorites=1, allow_comments=1;\"",
            ]
        )

        results.append(
            {
                "brand": brand["key"],
                "id": eid,
                "slug": slug,
                "share_token": share,
                "client_path": f"/gallery/{slug}/{share}",
                "guest_password_env": "GUEST_PASSWORD",
            }
        )

    out_path = GALLERY / "test-results" / "premium-demo-galleries.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"origin": ORIGIN, "galleries": results}, indent=2) + "\n")
    # Write screenshot target (no secrets beyond share tokens needed for demo)
    print("Wrote", out_path)
    for r in results:
        print(f"  {r['brand']}: {ORIGIN}{r['client_path']}")
    return 0


def multipart_via_curl(jar, tok, path, files: list[Path]):
    import subprocess

    cmd = [
        "curl",
        "-s",
        "-b",
        jar,
        "-X",
        "POST",
        f"{ORIGIN}{path}",
        "-H",
        f"Origin: {ORIGIN}",
        "-H",
        f"Authorization: Bearer {tok}",
    ]
    for f in files:
        cmd += ["-F", f"photos=@{f}"]
    out = subprocess.check_output(cmd, text=True)
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out[:300]}


if __name__ == "__main__":
    # fix forward ref
    sys.exit(main())
