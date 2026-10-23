#!/usr/bin/env python3
"""Capture desktop + mobile screenshots of running PicPeak ELP demo."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ORIGIN = os.environ.get("ORIGIN", "http://127.0.0.1:3000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "ElpStudioDemo2026!")
GUEST_PASS = os.environ.get("GUEST_PASSWORD", "GuestDemo1")
OUT = Path(
    os.environ.get(
        "SCREENSHOT_DIR",
        "/cursor/stores/bc-01a167cd-e78a-770b-835c-1af812a43b45/media/gallery-prototype",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

galleries_path = Path(__file__).resolve().parents[1] / "test-results" / "premium-demo-galleries.json"
if galleries_path.exists():
    data = json.loads(galleries_path.read_text())
    galleries = data["galleries"]
else:
    galleries = []

# Prefer Mini Momentz for primary client shots; fall back to first
primary = next((g for g in galleries if g["brand"] == "mini-momentz"), galleries[0] if galleries else None)
katha = next((g for g in galleries if g["brand"] == "katha-films"), None)


def shot(page, name: str) -> Path:
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return path


def dismiss_dialogs(page):
    page.keyboard.press("Escape")
    page.evaluate("() => document.querySelectorAll('dialog[open]').forEach(d => d.close())")
    time.sleep(0.3)


def guest_enter(page, url: str):
    page.goto(url, wait_until="networkidle", timeout=90000)
    time.sleep(1.2)
    gp = page.locator('input[type="password"]').first
    if gp.count():
        gp.fill(GUEST_PASS)
        clicked = False
        for name in ["View Gallery", "Enter Gallery", "Enter", "Unlock", "Open", "Continue"]:
            btn = page.get_by_role("button", name=name)
            if btn.count():
                btn.first.click()
                clicked = True
                break
        if not clicked:
            page.locator('button[type="submit"]').first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2.5)


def main() -> int:
    if not primary:
        print("No galleries found — run seed-premium-demo.py first", file=sys.stderr)
        return 1

    gallery_url = f"{ORIGIN}{primary['client_path']}"
    katha_url = f"{ORIGIN}{katha['client_path']}" if katha else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Admin desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"{ORIGIN}/admin", wait_until="networkidle", timeout=90000)
        time.sleep(1)
        shot(page, "01-admin-login-desktop.png")
        page.locator('input[type="email"]').fill(ADMIN_EMAIL)
        page.locator('input[type="password"]').fill(ADMIN_PASS)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/admin/**", timeout=20000)
        time.sleep(1.5)
        dismiss_dialogs(page)
        shot(page, "02-admin-dashboard-desktop.png")
        page.goto(f"{ORIGIN}/admin/events", wait_until="networkidle")
        time.sleep(1.2)
        dismiss_dialogs(page)
        shot(page, "03-admin-events-desktop.png")
        ctx.close()

        # Admin mobile
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
        )
        page = mctx.new_page()
        page.goto(f"{ORIGIN}/admin", wait_until="networkidle", timeout=90000)
        page.locator('input[type="email"]').fill(ADMIN_EMAIL)
        page.locator('input[type="password"]').fill(ADMIN_PASS)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/admin/**", timeout=20000)
        time.sleep(1.5)
        dismiss_dialogs(page)
        page.goto(f"{ORIGIN}/admin/events", wait_until="networkidle")
        time.sleep(1)
        dismiss_dialogs(page)
        shot(page, "08-admin-events-mobile.png")
        mctx.close()

        # Client desktop — password + gallery (Mini Momentz)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(gallery_url, wait_until="networkidle", timeout=90000)
        time.sleep(1.2)
        shot(page, "04-client-password-gate-desktop.png")
        guest_enter(page, gallery_url)
        shot(page, "05-client-gallery-desktop.png")
        # Scroll a bit to show grid
        page.mouse.wheel(0, 600)
        time.sleep(0.8)
        shot(page, "05b-client-gallery-grid-desktop.png")
        ctx.close()

        # Client mobile
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        page = mctx.new_page()
        page.goto(gallery_url, wait_until="networkidle", timeout=90000)
        time.sleep(1)
        shot(page, "06-client-password-gate-mobile.png")
        guest_enter(page, gallery_url)
        shot(page, "07-client-gallery-mobile.png")
        mctx.close()

        # Katha brand client (desktop) if available
        if katha_url:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            guest_enter(page, katha_url)
            shot(page, "09-client-katha-films-desktop.png")
            ctx.close()

        browser.close()

    manifest = OUT / "README.md"
    lines = [
        "# Gallery prototype screenshots",
        "",
        f"Captured against `{ORIGIN}` at `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`.",
        "",
        f"Primary client gallery: `{gallery_url}` (Mini Momentz demo).",
        "",
        "| File | Description |",
        "| --- | --- |",
        "| `01-admin-login-desktop.png` | Admin login |",
        "| `02-admin-dashboard-desktop.png` | Admin dashboard (multi-brand events) |",
        "| `03-admin-events-desktop.png` | Events list — Mini Momentz / Katha / Tattva |",
        "| `04-client-password-gate-desktop.png` | Client password gate |",
        "| `05-client-gallery-desktop.png` | Client gallery with hero cover |",
        "| `05b-client-gallery-grid-desktop.png` | Client photo grid |",
        "| `06-client-password-gate-mobile.png` | Password gate (mobile) |",
        "| `07-client-gallery-mobile.png` | Client gallery (mobile) |",
        "| `08-admin-events-mobile.png` | Admin events (mobile) |",
        "| `09-client-katha-films-desktop.png` | Katha Films branded client view |",
        "| `SMOKE_TEST_RESULTS.md` | Automated smoke results |",
        "",
    ]
    for f in sorted(OUT.glob("*.png")):
        lines.append(f"- `{f.name}` ({f.stat().st_size} bytes)")
    manifest.write_text("\n".join(lines) + "\n")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
