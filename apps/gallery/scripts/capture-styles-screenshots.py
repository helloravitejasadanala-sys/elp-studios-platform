#!/usr/bin/env python3
"""Capture desktop + mobile screenshots for Style A (Tattva) and Style B (Mini Momentz).

Default prefix via SHOT_PREFIX (e.g. 23). Does not overwrite 01–13 proof shots.
Emphasises full gallery page + photo viewing for both styles.
"""
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
PREFIX = os.environ.get("SHOT_PREFIX", "23")
OUT = Path(
    os.environ.get(
        "SCREENSHOT_DIR",
        "/cursor/stores/bc-01a167cd-e78a-770b-835c-1af812a43b45/media/gallery-prototype",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

meta_path = Path(__file__).resolve().parents[1] / "test-results" / "styles-demo-galleries.json"
if not meta_path.exists():
    print("Run seed-styles-demo.py first", file=sys.stderr)
    sys.exit(1)
data = json.loads(meta_path.read_text())
galleries = {g["brand"]: g for g in data["galleries"]}
tattva = galleries.get("tattva-weddings")
mini = galleries.get("mini-momentz")
if not tattva or not mini:
    print("Need both tattva-weddings and mini-momentz in styles-demo-galleries.json", file=sys.stderr)
    sys.exit(1)


def shot(page, name: str) -> Path:
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return path


def dismiss_dialogs(page):
    page.keyboard.press("Escape")
    try:
        page.evaluate("() => document.querySelectorAll('dialog[open]').forEach(d => d.close())")
    except Exception:
        pass
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


def open_photo_view(page) -> bool:
    """Open a set then a photo for fullscreen/lightbox view."""
    folders = page.locator("button.group")
    if folders.count():
        try:
            folders.first.click(timeout=3000)
            page.wait_for_load_state("networkidle")
            time.sleep(1.5)
        except Exception:
            pass
    cards = page.locator(".photo-card")
    if cards.count():
        try:
            cards.first.click(timeout=3000)
            time.sleep(1.8)
            return True
        except Exception:
            pass
    return False


def capture_brand(browser, g: dict, slug: str):
    url = f"{ORIGIN}{g['client_path']}"
    label = f"{g['brand_display']} / {g['style_display']}"

    # Desktop — full gallery + photo view
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    guest_enter(page, url)
    # Scroll to top for full gallery composition (hero + folders)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.6)
    shot(page, f"{PREFIX}-{slug}-gallery-desktop.png")
    # Also a mid-page sets view
    page.mouse.wheel(0, 520)
    time.sleep(0.7)
    shot(page, f"{PREFIX}-{slug}-sets-desktop.png")
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.4)
    if open_photo_view(page):
        shot(page, f"{PREFIX}-{slug}-photo-view-desktop.png")
        page.keyboard.press("Escape")
        time.sleep(0.4)
    ctx.close()

    # Mobile — full gallery + photo view
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
    guest_enter(page, url)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.6)
    shot(page, f"{PREFIX}-{slug}-gallery-mobile.png")
    page.mouse.wheel(0, 400)
    time.sleep(0.6)
    shot(page, f"{PREFIX}-{slug}-sets-mobile.png")
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.3)
    if open_photo_view(page):
        shot(page, f"{PREFIX}-{slug}-photo-view-mobile.png")
    mctx.close()
    print(f"done {label}")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        capture_brand(browser, tattva, "tattva-editorial")
        capture_brand(browser, mini, "mini-modern")
        browser.close()

    index = OUT / "REFINE_SCREENSHOTS.md"
    lines = [
        "# Style A/B UI refine screenshots",
        "",
        f"Captured against `{ORIGIN}` at `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`.",
        f"Prefix: `{PREFIX}-*`",
        "",
        "Changes: Soft Ivory hero titles on dark covers (Tattva); Mini logo soft plate (no transparent asset); larger Tattva logo; folder/spacing polish.",
        "",
        f"- Tattva: `{ORIGIN}{tattva['client_path']}`",
        f"- Mini: `{ORIGIN}{mini['client_path']}`",
        "",
        "| File | Description |",
        "| --- | --- |",
        f"| `{PREFIX}-tattva-editorial-gallery-desktop.png` | Tattva full gallery (desktop) |",
        f"| `{PREFIX}-tattva-editorial-gallery-mobile.png` | Tattva full gallery (mobile) |",
        f"| `{PREFIX}-tattva-editorial-photo-view-desktop.png` | Tattva photo view (desktop) |",
        f"| `{PREFIX}-tattva-editorial-photo-view-mobile.png` | Tattva photo view (mobile) |",
        f"| `{PREFIX}-mini-modern-gallery-desktop.png` | Mini full gallery (desktop) |",
        f"| `{PREFIX}-mini-modern-gallery-mobile.png` | Mini full gallery (mobile) |",
        f"| `{PREFIX}-mini-modern-photo-view-desktop.png` | Mini photo view (desktop) |",
        f"| `{PREFIX}-mini-modern-photo-view-mobile.png` | Mini photo view (mobile) |",
        "",
        "## PNG sizes",
        "",
    ]
    for f in sorted(OUT.glob(f"{PREFIX}-*.png")):
        lines.append(f"- `{f.name}` ({f.stat().st_size} bytes)")
    index.write_text("\n".join(lines) + "\n")
    print(f"wrote {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
