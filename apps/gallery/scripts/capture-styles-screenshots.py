#!/usr/bin/env python3
"""Capture desktop + mobile screenshots for Style A (Tattva) and Style B (Mini Momentz).

Default prefix `22` (genuine logos). Override with SHOT_PREFIX=20 to refresh older series.
Does not overwrite 01–13 proof shots.
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
PREFIX = os.environ.get("SHOT_PREFIX", "22")
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


def capture_brand(browser, g: dict, prefix: str):
    url = f"{ORIGIN}{g['client_path']}"
    label = f"{g['brand_display']} / {g['style_display']}"

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(url, wait_until="networkidle", timeout=90000)
    time.sleep(1.2)
    shot(page, f"{prefix}-password-desktop.png")
    guest_enter(page, url)
    shot(page, f"{prefix}-cover-desktop.png")
    page.mouse.wheel(0, 700)
    time.sleep(0.9)
    shot(page, f"{prefix}-sets-grid-desktop.png")

    imgs = page.locator("img").all()
    opened = False
    for img in imgs[1:8]:
        try:
            img.click(timeout=2000)
            time.sleep(1.5)
            opened = True
            break
        except Exception:
            continue
    if opened:
        shot(page, f"{prefix}-photo-view-desktop.png")
        page.keyboard.press("Escape")
        time.sleep(0.5)
    ctx.close()

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
    page.goto(url, wait_until="networkidle", timeout=90000)
    time.sleep(1)
    shot(page, f"{prefix}-password-mobile.png")
    guest_enter(page, url)
    shot(page, f"{prefix}-cover-mobile.png")
    page.mouse.wheel(0, 500)
    time.sleep(0.8)
    shot(page, f"{prefix}-sets-grid-mobile.png")
    mctx.close()
    print(f"done {label}")


def main() -> int:
    tattva_prefix = f"{PREFIX}-tattva-editorial"
    mini_prefix = f"{PREFIX}-mini-modern"
    admin_name = f"{PREFIX}-admin-events-logos-desktop.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"{ORIGIN}/admin", wait_until="networkidle", timeout=90000)
        time.sleep(0.8)
        email = page.locator('input[type="email"]')
        user = page.locator('input[name="username"], input[type="text"]').first
        if email.count():
            email.fill(ADMIN_EMAIL)
        elif user.count():
            user.fill(os.environ.get("ADMIN_USERNAME", "admin"))
        page.locator('input[type="password"]').fill(ADMIN_PASS)
        for name in ["Sign In", "Log in", "Login"]:
            btn = page.get_by_role("button", name=name)
            if btn.count():
                btn.first.click()
                break
        page.wait_for_url("**/admin/**", timeout=25000)
        time.sleep(1.5)
        dismiss_dialogs(page)
        page.goto(f"{ORIGIN}/admin/events", wait_until="networkidle")
        time.sleep(1.2)
        dismiss_dialogs(page)
        shot(page, admin_name)
        ctx.close()

        capture_brand(browser, tattva, tattva_prefix)
        capture_brand(browser, mini, mini_prefix)

        browser.close()

    index = OUT / "LOGOS_SCREENSHOTS.md"
    lines = [
        "# Genuine logo screenshots (Style A + Style B)",
        "",
        f"Captured against `{ORIGIN}` at `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`.",
        f"Prefix: `{PREFIX}-*`",
        "",
        f"- **Tattva** (Deep Crimson primary SVG): `{ORIGIN}{tattva['client_path']}`",
        f"- **Mini Momentz** (colour logo): `{ORIGIN}{mini['client_path']}`",
        "",
        "Fonts remain documented fallbacks until licensed files are supplied.",
        "",
        "| File | Description |",
        "| --- | --- |",
        f"| `{admin_name}` | Admin events (ELP + client galleries) |",
        f"| `{tattva_prefix}-password-desktop.png` | Tattva password + logo |",
        f"| `{tattva_prefix}-cover-desktop.png` | Tattva cover / hero + logo |",
        f"| `{tattva_prefix}-sets-grid-desktop.png` | Tattva sets |",
        f"| `{tattva_prefix}-photo-view-desktop.png` | Tattva photo view |",
        f"| `{tattva_prefix}-*-mobile.png` | Tattva mobile |",
        f"| `{mini_prefix}-*-desktop.png` / `*-mobile.png` | Mini Momentz |",
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
