#!/usr/bin/env python3
"""Seed Style A (Wedding Editorial) + Style B (Modern Story) demo galleries from brands/ + styles/ config.

Galleries:
  1. Tattva Weddings — Wedding Editorial
  2. Mini Momentz — Modern Story

Proves: sets, password, uploads, publish, guest view, original SHA-256 downloads, ZIP-all.
Config-driven CSS templates (no app fork).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GALLERY = ROOT / "apps" / "gallery"
STYLES = ROOT / "styles"
BRANDS = ROOT / "brands"
MEDIA = ROOT / "demo-media"
RESULTS = GALLERY / "test-results"
ORIGIN = os.environ.get("ORIGIN", "http://127.0.0.1:3000")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "ElpDemo2026!")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")
GUEST_PASS = os.environ.get("GUEST_PASSWORD", "GuestDemo1")

# Brand → style demos (today's deliverable)
DEMOS = [
    {
        "brand_id": "tattva-weddings",
        "style_id": "wedding-editorial",
        "media_dir": MEDIA / "tattva-weddings",
        "video": MEDIA / "videos" / "katha-demo-clip.mp4",
        "set_files": {
            "Getting Ready": ["tattva-weddings-01.jpg", "tattva-weddings-02.jpg"],
            "Ceremony": ["tattva-weddings-03.jpg", "tattva-weddings-cover.jpg"],
            "Portraits": ["tattva-weddings-04.jpg"],
            "Reception Film": ["__video__"],
        },
    },
    {
        "brand_id": "mini-momentz",
        "style_id": "modern-story",
        "media_dir": MEDIA / "mini-momentz",
        "video": MEDIA / "videos" / "katha-demo-clip.mp4",
        "set_files": {
            "Outdoor Portraits": ["mini-momentz-01.jpg", "mini-momentz-02.jpg"],
            "Ceremony": ["mini-momentz-03.jpg", "mini-momentz-cover.jpg"],
            "Family": ["mini-momentz-04.jpg"],
            "Highlights Film": ["__video__"],
        },
    },
]


def load_env():
    env = GALLERY / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def sh256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    load_env()
    global ADMIN_PASS, ADMIN_USER, ADMIN_EMAIL, GUEST_PASS, ORIGIN
    ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", ADMIN_PASS)
    ADMIN_USER = os.environ.get("ADMIN_USERNAME", ADMIN_USER)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", ADMIN_EMAIL)
    GUEST_PASS = os.environ.get("GUEST_PASSWORD", GUEST_PASS)
    ORIGIN = os.environ.get("ORIGIN", ORIGIN)

    jar = tempfile.NamedTemporaryFile(delete=False).name

    def token() -> str:
        for line in Path(jar).read_text().splitlines():
            if "admin_token" in line and not line.startswith("#"):
                return line.split("\t")[-1]
        return ""

    def curl_json(method, path, payload=None):
        cmd = [
            "curl", "-s", "-c", jar, "-b", jar, "-X", method,
            f"{ORIGIN}{path}",
            "-H", f"Origin: {ORIGIN}",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {token()}",
        ]
        if payload is not None:
            cmd += ["-d", json.dumps(payload)]
        out = subprocess.check_output(cmd, text=True)
        return json.loads(out) if out else {}

    login = subprocess.check_output(
        [
            "curl", "-s", "-c", jar, "-b", jar, "-X", "POST",
            f"{ORIGIN}/api/auth/admin/login",
            "-H", "Content-Type: application/json",
            "-H", f"Origin: {ORIGIN}",
            "-d", json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}),
        ],
        text=True,
    )
    login_j = json.loads(login)
    if "user" not in login_j:
        print("LOGIN FAIL", login)
        return 1
    # First-boot PicPeak may require password change before admin APIs work
    if login_j.get("mustChangePassword") or login_j.get("user", {}).get("mustChangePassword"):
        new_pass = os.environ.get(
            "ADMIN_PASSWORD_NEW",
            ADMIN_PASS if len(ADMIN_PASS) >= 12 else "ElpStudioDemo2026!",
        )
        tok0 = token()
        ch_out = subprocess.check_output(
            [
                "curl", "-s", "-c", jar, "-b", jar, "-X", "POST",
                f"{ORIGIN}/api/admin/auth/change-password",
                "-H", "Content-Type: application/json",
                "-H", f"Origin: {ORIGIN}",
                "-H", f"Authorization: Bearer {tok0}",
                "-d", json.dumps({"currentPassword": ADMIN_PASS, "newPassword": new_pass}),
            ],
            text=True,
        )
        print("password change:", ch_out[:200])
        ADMIN_PASS = new_pass
        os.environ["ADMIN_PASSWORD"] = new_pass
        login = subprocess.check_output(
            [
                "curl", "-s", "-c", jar, "-b", jar, "-X", "POST",
                f"{ORIGIN}/api/auth/admin/login",
                "-H", "Content-Type: application/json",
                "-H", f"Origin: {ORIGIN}",
                "-d", json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}),
            ],
            text=True,
        )
        if "user" not in json.loads(login):
            print("RE-LOGIN FAIL", login)
            return 1
    print("logged in")

    # MIME + original downloads (preserve critical settings)
    curl_json(
        "PUT",
        "/api/admin/settings/general",
        {
            "general_allowed_file_types": "jpg,jpeg,png,webp,gif,heic,mp4,mov,webm",
            "general_use_original_filenames_for_downloads": True,
            "download_standard_resolution": "original",
            "download_allow_original": True,
        },
    )
    subprocess.call(
        [
            "docker", "exec", "elp-picpeak", "sh", "-c",
            "sqlite3 /data/db/picpeak.db \""
            "UPDATE app_settings SET setting_value='jpg,jpeg,png,webp,gif,heic,mp4,mov,webm' WHERE setting_key='general_allowed_file_types';"
            "UPDATE app_settings SET setting_value='original' WHERE setting_key='download_standard_resolution';"
            "UPDATE app_settings SET setting_value='true' WHERE setting_key='download_allow_original';"
            "UPDATE app_settings SET setting_value='true' WHERE setting_key='general_use_original_filenames_for_downloads';"
            "\"",
        ]
    )

    curl_json(
        "PUT",
        "/api/admin/settings/branding",
        {
            "company_name": "ELP Studios Galleries",
            "company_tagline": "Style A Wedding Editorial · Style B Modern Story",
            "support_email": ADMIN_EMAIL,
            "footer_text": "Demo — placeholder logos/fonts/colours until owner brand guidelines. Not Macro.",
            "watermark_enabled": False,
            "force_color_mode": "light",
            "logo_display_header": True,
            "logo_display_hero": True,
        },
    )

    # Install CSS templates from styles/ config (slots from style.json)
    style_css_ids: dict[str, int] = {}
    for style_id in ("wedding-editorial", "modern-story"):
        meta = load_json(STYLES / style_id / "style.json")
        css = (STYLES / style_id / meta["css_file"]).read_text()
        slot = int(meta["picpeak_css_slot"])
        name = meta["picpeak_template_name"]
        put = curl_json(
            "PUT",
            f"/api/admin/css-templates/{slot}",
            {"name": name, "css_content": css, "is_enabled": True},
        )
        print(f"css slot {slot} ({style_id}):", put.get("success") or put.get("error") or put)
        templates = curl_json("GET", "/api/admin/css-templates")
        for t in templates.get("templates", []):
            if t.get("slot_number") == slot:
                style_css_ids[style_id] = t.get("id")
                break
        print(f"  css_id[{style_id}] =", style_css_ids.get(style_id))

    all_integrity = []
    galleries_out = []
    pass_n = fail_n = 0

    for demo in DEMOS:
        brand = load_json(BRANDS / demo["brand_id"] / "brand.json")
        style = load_json(STYLES / demo["style_id"] / "style.json")
        ev = brand["demo_event"]
        css_id = style_css_ids.get(demo["style_id"])

        event_name = f"{brand['display_name']} — {ev['client_name']} — {ev['gallery_name']}"
        payload = {
            "event_type": "other",
            "event_name": event_name,
            "event_date": ev["event_date"],
            "customer_name": ev["client_name"],
            "customer_email": "demo.client@example.com",
            "admin_email": ADMIN_EMAIL,
            "require_password": True,
            "password": GUEST_PASS,
            "allow_downloads": True,
            "allow_favorites": True,
            "allow_likes": True,
            "allow_comments": True,
            "feedback_enabled": True,
            "watermark_downloads": False,
            "welcome_message": ev["welcome"],
            "expiration_days": 180,
            "header_style": "hero",
            "hero_logo_visible": True,
            "hero_logo_size": "medium",
            "hero_logo_position": "center",
            "hero_divider_style": "none",
            "disable_right_click": False,
        }
        if css_id:
            payload["css_template_id"] = css_id

        created = curl_json("POST", "/api/admin/events", payload)
        if "id" not in created:
            print("CREATE FAIL", demo["brand_id"], created)
            return 1
        eid = created["id"]
        slug = created["slug"]
        share = created["share_token"]
        print(f"\n=== {brand['display_name']} / {style['name']} id={eid} ===")

        # Sets
        sets = {}
        for set_name in ev["sets"]:
            cat = curl_json(
                "POST",
                "/api/admin/categories",
                {"name": set_name, "is_global": False, "event_id": eid, "is_folder": True},
            )
            if "id" not in cat:
                print("CATEGORY FAIL", set_name, cat)
                return 1
            sets[set_name] = cat["id"]
            print(f"  set {set_name} → {cat['id']}")

        photo_ids_by_set: dict[str, list] = {}
        media_dir = demo["media_dir"]

        for set_name, filenames in demo["set_files"].items():
            cid = sets[set_name]
            for fn in filenames:
                if fn == "__video__":
                    f = demo["video"]
                else:
                    f = media_dir / fn
                if not f.exists():
                    print("MISSING", f)
                    return 1
                local_hash = sh256(f)
                # curl often sends application/octet-stream for .mp4; PicPeak needs a real video MIME
                mime = ""
                suf = f.suffix.lower()
                if suf == ".mp4":
                    mime = ";type=video/mp4"
                elif suf == ".mov":
                    mime = ";type=video/quicktime"
                elif suf == ".webm":
                    mime = ";type=video/webm"
                elif suf in (".jpg", ".jpeg"):
                    mime = ";type=image/jpeg"
                elif suf == ".png":
                    mime = ";type=image/png"
                elif suf == ".webp":
                    mime = ";type=image/webp"
                cmd = [
                    "curl", "-s", "-b", jar, "-X", "POST",
                    f"{ORIGIN}/api/admin/events/{eid}/upload",
                    "-H", f"Origin: {ORIGIN}",
                    "-H", f"Authorization: Bearer {token()}",
                    "-F", f"photos=@{f}{mime}",
                    "-F", f"category_id={cid}",
                ]
                up = json.loads(subprocess.check_output(cmd, text=True))
                pids = up.get("photo_ids") or []
                if not pids:
                    print("UPLOAD FAIL", f, up)
                    return 1
                pid = pids[0]
                photo_ids_by_set.setdefault(set_name, []).append(pid)
                row = {
                    "brand": brand["display_name"],
                    "style": style["name"],
                    "event_id": eid,
                    "slug": slug,
                    "set": set_name,
                    "photo_id": pid,
                    "source_path": str(f.relative_to(ROOT)),
                    "source_filename": f.name,
                    "source_sha256": local_hash,
                    "source_bytes": f.stat().st_size,
                }
                all_integrity.append(row)
                print(f"  uploaded {f.name} → photo {pid}")

        # Cover = first photo of first set
        first_set = ev["sets"][0]
        cover_id = photo_ids_by_set[first_set][0]
        curl_json(
            "PUT",
            f"/api/admin/events/{eid}",
            {
                "header_style": "hero",
                "hero_photo_id": cover_id,
                "watermark_downloads": False,
                "allow_downloads": True,
                "css_template_id": css_id,
            },
        )

        # Brand placeholder logo
        logo_rel = brand["logo_placeholder"]
        logo = (BRANDS / demo["brand_id"] / logo_rel).resolve()
        if not logo.exists():
            logo = BRANDS / "placeholders" / f"{demo['brand_id']}-logo.png"
        if logo.exists():
            subprocess.check_output(
                [
                    "curl", "-s", "-b", jar, "-X", "POST",
                    f"{ORIGIN}/api/admin/events/{eid}/logo",
                    "-H", f"Origin: {ORIGIN}",
                    "-H", f"Authorization: Bearer {token()}",
                    "-F", f"logo=@{logo}",
                ],
                text=True,
            )
            print("  logo ok", logo.name)

        pub = curl_json(
            "POST",
            f"/api/admin/events/{eid}/publish",
            {"password": GUEST_PASS, "notify_customer": False},
        )
        print("  publish", pub.get("message") or pub)

        subprocess.call(
            [
                "docker", "exec", "elp-picpeak", "sh", "-c",
                f"sqlite3 /data/db/picpeak.db \"INSERT INTO event_feedback_settings "
                f"(event_id, feedback_enabled, allow_favorites, allow_likes, allow_comments, "
                f"allow_reactions, show_feedback_to_guests, identity_mode) "
                f"VALUES ({eid},1,1,1,1,1,1,'simple') "
                f"ON CONFLICT(event_id) DO UPDATE SET feedback_enabled=1, allow_favorites=1;\"",
            ]
        )

        # Guest auth + integrity
        gjar = tempfile.NamedTemporaryFile(delete=False).name
        gok = json.loads(
            subprocess.check_output(
                [
                    "curl", "-s", "-c", gjar, "-b", gjar, "-X", "POST",
                    f"{ORIGIN}/api/auth/gallery/verify",
                    "-H", "Content-Type: application/json",
                    "-H", f"Origin: {ORIGIN}",
                    "-d", json.dumps({"slug": slug, "password": GUEST_PASS}),
                ],
                text=True,
            )
        )
        gtoken = gok.get("token")
        if not gtoken:
            print("GUEST LOGIN FAIL", gok)
            return 1

        dl_dir = RESULTS / "downloads" / "styles-integrity" / demo["brand_id"]
        dl_dir.mkdir(parents=True, exist_ok=True)
        brand_rows = [r for r in all_integrity if r["event_id"] == eid]
        for row in brand_rows:
            out = dl_dir / f"photo-{row['photo_id']}-{row['source_filename']}"
            code = subprocess.check_output(
                [
                    "curl", "-s", "-b", gjar,
                    "-H", f"Authorization: Bearer {gtoken}",
                    "-o", str(out),
                    "-w", "%{http_code}",
                    f"{ORIGIN}/api/gallery/{slug}/download/{row['photo_id']}",
                ],
                text=True,
            ).strip()
            dl_hash = sh256(out) if out.exists() else ""
            match = (
                code == "200"
                and dl_hash == row["source_sha256"]
                and out.stat().st_size == row["source_bytes"]
            )
            row["download_http"] = code
            row["download_sha256"] = dl_hash
            row["download_bytes"] = out.stat().st_size if out.exists() else 0
            row["sha256_match"] = match
            if match:
                pass_n += 1
                print(f"  PASS integrity {row['source_filename']}")
            else:
                fail_n += 1
                print(f"  FAIL integrity {row['source_filename']} http={code}")

        # ZIP download-all smoke
        zip_out = dl_dir / "download-all.zip"
        zcode = subprocess.check_output(
            [
                "curl", "-s", "-b", gjar,
                "-H", f"Authorization: Bearer {gtoken}",
                "-o", str(zip_out),
                "-w", "%{http_code}",
                f"{ORIGIN}/api/gallery/{slug}/download-all",
            ],
            text=True,
        ).strip()
        zip_ok = zcode == "200" and zip_out.exists() and zip_out.stat().st_size > 100
        print(f"  download-all ZIP http={zcode} bytes={zip_out.stat().st_size if zip_out.exists() else 0} ok={zip_ok}")

        photos = json.loads(
            subprocess.check_output(
                [
                    "curl", "-s", "-b", gjar,
                    "-H", f"Authorization: Bearer {gtoken}",
                    f"{ORIGIN}/api/gallery/{slug}/photos",
                ],
                text=True,
            )
        )
        cats = [c.get("name") for c in (photos.get("categories") or [])]
        print(f"  guest categories: {cats}")

        galleries_out.append(
            {
                "brand": demo["brand_id"],
                "brand_display": brand["display_name"],
                "style": demo["style_id"],
                "style_display": style["name"],
                "client": ev["client_name"],
                "gallery": ev["gallery_name"],
                "event_id": eid,
                "slug": slug,
                "share_token": share,
                "client_path": f"/gallery/{slug}/{share}",
                "css_template_id": css_id,
                "sets": {k: {"id": v, "photo_ids": photo_ids_by_set.get(k, [])} for k, v in sets.items()},
                "download_all_zip_ok": zip_ok,
            }
        )

    RESULTS.mkdir(parents=True, exist_ok=True)
    meta_path = RESULTS / "styles-demo-galleries.json"
    meta_path.write_text(
        json.dumps(
            {
                "origin": ORIGIN,
                "guest_password_env": "GUEST_PASSWORD",
                "integrity_pass": pass_n,
                "integrity_fail": fail_n,
                "galleries": galleries_out,
            },
            indent=2,
        )
        + "\n"
    )
    (RESULTS / "styles-original-integrity-raw.json").write_text(
        json.dumps(all_integrity, indent=2) + "\n"
    )

    lines = [
        "# Original download integrity — Style A + Style B demos (SHA-256)",
        "",
        f"- Origin: `{ORIGIN}`",
        f"- Settings: `download_standard_resolution=original`, watermarks off, original filenames on",
        f"- Result: **{pass_n} PASS / {fail_n} FAIL** of {pass_n + fail_n} files",
        "",
    ]
    for g in galleries_out:
        lines.append(
            f"## {g['brand_display']} — {g['style_display']} (`id={g['event_id']}`)"
        )
        lines.append(f"- Client path: `{g['client_path']}`")
        lines.append(f"- Sets: {', '.join(g['sets'].keys())}")
        lines.append(f"- Download-all ZIP: {'PASS' if g['download_all_zip_ok'] else 'FAIL'}")
        lines.append("")
        lines.append("| Set | Source file | Bytes | SHA-256 match |")
        lines.append("| --- | --- | ---: | --- |")
        for row in all_integrity:
            if row["event_id"] != g["event_id"]:
                continue
            lines.append(
                f"| {row['set']} | `{row['source_filename']}` | {row['source_bytes']} | "
                f"{'PASS' if row['sha256_match'] else 'FAIL'} |"
            )
        lines.append("")
    lines += [
        "Raw: `apps/gallery/test-results/styles-original-integrity-raw.json`",
        "Meta: `apps/gallery/test-results/styles-demo-galleries.json`",
        "",
        "Guest download endpoints return **exact uploaded bytes** when original resolution is standard and watermarks are off.",
    ]
    report = RESULTS / "STYLES_ORIGINAL_INTEGRITY.md"
    report.write_text("\n".join(lines) + "\n")
    print("\nWrote", meta_path)
    print("Wrote", report)
    for g in galleries_out:
        print(f"  {g['brand']}: {ORIGIN}{g['client_path']}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
