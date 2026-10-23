#!/usr/bin/env python3
"""Capture desktop + mobile screenshots of running PicPeak demo UI."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ORIGIN = os.environ.get("ORIGIN", "http://127.0.0.1:3000")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "ElpStudioDemo2026!")
GUEST_PASS = os.environ.get("GUEST_PASSWORD", "GuestDemo1")
OUT = Path(
    os.environ.get(
        "SCREENSHOT_DIR",
        "/cursor/stores/bc-01a167cd-e78a-770b-835c-1af812a43b45/media/gallery-prototype",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

# Prefer last smoke event; fall back to known demo
event_path = Path(__file__).resolve().parents[1] / "test-results" / "last-event.json"
if event_path.exists():
    event = json.loads(event_path.read_text())
else:
    event = {
        "slug": "other-mini-momentz-demo-family-session-2026-10-01",
        "share_token": "2b65b077144d09accd626689d3f36b93",
    }

SLUG = event["slug"]
SHARE = event["share_token"]
GALLERY_URL = f"{ORIGIN}/gallery/{SLUG}/{SHARE}"
ADMIN_URL = f"{ORIGIN}/admin"


def shot(page, name: str) -> Path:
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return path


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Desktop admin ---
        desktop = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = desktop.new_page()
        page.goto(ADMIN_URL, wait_until="networkidle", timeout=60000)
        time.sleep(1)
        shot(page, "01-admin-login-desktop.png")

        # Fill login if form present
        email = page.locator('input[type="email"], input[name="email"], input[autocomplete="username"]').first
        pwd = page.locator('input[type="password"]').first
        if email.count() and pwd.count():
            # PicPeak admin login uses email (ADMIN_EMAIL), not username
            email.fill(os.environ.get("ADMIN_EMAIL", "admin@elp.local"))
            pwd.fill(ADMIN_PASS)
            page.get_by_role("button", name="Sign In").click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            page.keyboard.press("Escape")
            page.evaluate("() => document.querySelectorAll('dialog[open]').forEach(d => d.close())")
            time.sleep(0.3)
        shot(page, "02-admin-after-login-desktop.png")

        # Try navigate to events list
        for sel in [
            'a[href*="event"]',
            'text=Events',
            'text=Galleries',
            'text=Dashboard',
        ]:
            loc = page.locator(sel).first
            if loc.count():
                try:
                    loc.click(timeout=2000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    break
                except Exception:
                    pass
        shot(page, "03-admin-events-desktop.png")
        desktop.close()

        # --- Desktop client gallery (password gate) ---
        desktop2 = browser.new_context(viewport={"width": 1440, "height": 900})
        page = desktop2.new_page()
        page.goto(GALLERY_URL, wait_until="networkidle", timeout=60000)
        time.sleep(1.5)
        shot(page, "04-client-password-gate-desktop.png")

        gp = page.locator('input[type="password"]').first
        if gp.count():
            gp.fill(GUEST_PASS)
            page.locator('button[type="submit"], button:has-text("Enter"), button:has-text("View"), button:has-text("Unlock"), button:has-text("Open")').first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2.5)
        shot(page, "05-client-gallery-desktop.png")
        desktop2.close()

        # --- Mobile client ---
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        page = mobile.new_page()
        page.goto(GALLERY_URL, wait_until="networkidle", timeout=60000)
        time.sleep(1.5)
        shot(page, "06-client-password-gate-mobile.png")
        gp = page.locator('input[type="password"]').first
        if gp.count():
            gp.fill(GUEST_PASS)
            btn = page.locator('button[type="submit"], button:has-text("Enter"), button:has-text("View"), button:has-text("Unlock"), button:has-text("Open")').first
            if btn.count():
                btn.click()
            else:
                gp.press("Enter")
            page.wait_for_load_state("networkidle")
            time.sleep(2.5)
        shot(page, "07-client-gallery-mobile.png")
        mobile.close()

        browser.close()

    # Manifest
    files = sorted(OUT.glob("*.png"))
    manifest = OUT / "README.md"
    lines = [
        "# Gallery prototype screenshots",
        "",
        f"Captured against `{ORIGIN}` at `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`.",
        "",
        f"Gallery URL used: `{GALLERY_URL}`",
        "",
        "| File | Description |",
        "| --- | --- |",
        "| `01-admin-login-desktop.png` | Admin login (desktop 1440×900) |",
        "| `02-admin-after-login-desktop.png` | Admin after login |",
        "| `03-admin-events-desktop.png` | Admin events / dashboard area |",
        "| `04-client-password-gate-desktop.png` | Client password gate (desktop) |",
        "| `05-client-gallery-desktop.png` | Client gallery grid (desktop) |",
        "| `06-client-password-gate-mobile.png` | Client password gate (mobile 390×844) |",
        "| `07-client-gallery-mobile.png` | Client gallery grid (mobile) |",
        "",
        "## Files present",
        "",
    ]
    for f in files:
        lines.append(f"- `{f.name}` ({f.stat().st_size} bytes)")
    manifest.write_text("\n".join(lines) + "\n")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
