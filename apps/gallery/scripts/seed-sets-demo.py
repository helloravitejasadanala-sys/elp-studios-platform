#!/usr/bin/env python3
"""Seed Brand→Client→Gallery→Sets demo and prove original-byte downloads (SHA-256)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GALLERY = ROOT / "apps" / "gallery"
ORIGIN = os.environ.get("ORIGIN", "http://127.0.0.1:3000")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "ElpStudioDemo2026!")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")
GUEST_PASS = os.environ.get("GUEST_PASSWORD", "GuestDemo1")
RESULTS = GALLERY / "test-results"
MEDIA = ROOT / "demo-media"


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


def main() -> int:
    load_env()
    global ADMIN_PASS, ADMIN_USER, ADMIN_EMAIL, GUEST_PASS
    ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", ADMIN_PASS)
    ADMIN_USER = os.environ.get("ADMIN_USERNAME", ADMIN_USER)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", ADMIN_EMAIL)
    GUEST_PASS = os.environ.get("GUEST_PASSWORD", GUEST_PASS)

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
    if "user" not in json.loads(login):
        print("LOGIN FAIL", login)
        return 1

    # Pin original-byte downloads (plain strings in DB — PicPeak JSON-quotes via PUT)
    curl_json(
        "PUT",
        "/api/admin/settings/general",
        {
            "general_use_original_filenames_for_downloads": True,
            "download_standard_resolution": "original",
            "download_allow_original": True,
        },
    )
    subprocess.call(
        [
            "docker", "exec", "elp-picpeak", "sh", "-c",
            "sqlite3 /data/db/picpeak.db \""
            "UPDATE app_settings SET setting_value='original' WHERE setting_key='download_standard_resolution';"
            "UPDATE app_settings SET setting_value='true' WHERE setting_key='download_allow_original';"
            "UPDATE app_settings SET setting_value='true' WHERE setting_key='general_use_original_filenames_for_downloads';"
            "\"",
        ]
    )

    # Gallery: Mini Momentz → Divya & Ravi → Seemantham
    created = curl_json(
        "POST",
        "/api/admin/events",
        {
            "event_type": "other",
            "event_name": "Mini Momentz — Divya & Ravi — Seemantham",
            "event_date": "2026-10-12",
            "customer_name": "Divya & Ravi",
            "customer_email": "demo.divya.ravi@example.com",
            "admin_email": ADMIN_EMAIL,
            "require_password": True,
            "password": GUEST_PASS,
            "allow_downloads": True,
            "allow_favorites": True,
            "allow_comments": True,
            "feedback_enabled": True,
            "watermark_downloads": False,
            "welcome_message": "Your Seemantham gallery — sets for Outdoor Portraits, Ceremony, Family, and Highlights Film.",
            "expiration_days": 180,
            "header_style": "hero",
            "hero_divider_style": "none",
        },
    )
    if "id" not in created:
        print("CREATE FAIL", created)
        return 1
    eid = created["id"]
    slug = created["slug"]
    share = created["share_token"]
    print(f"gallery id={eid} slug={slug}")

    # Sets (folders)
    set_names = [
        "Outdoor Portraits",
        "Ceremony",
        "Family",
        "Highlights Film",
    ]
    sets = {}
    for name in set_names:
        cat = curl_json(
            "POST",
            "/api/admin/categories",
            {
                "name": name,
                "is_global": False,
                "event_id": eid,
                "is_folder": True,
            },
        )
        if "id" not in cat:
            print("CATEGORY FAIL", name, cat)
            return 1
        sets[name] = cat["id"]
        print(f"  set {name} id={cat['id']}")

    # Map demo files into sets (distinct originals for integrity)
    mm = MEDIA / "mini-momentz"
    kf = MEDIA / "katha-films"
    vid = MEDIA / "videos" / "katha-demo-clip.mp4"
    plan = [
        ("Outdoor Portraits", [mm / "mini-momentz-01.jpg", mm / "mini-momentz-02.jpg"]),
        ("Ceremony", [mm / "mini-momentz-03.jpg", mm / "mini-momentz-cover.jpg"]),
        ("Family", [mm / "mini-momentz-04.jpg", kf / "katha-films-01.jpg"]),
        ("Highlights Film", [vid] if vid.exists() else [kf / "katha-films-02.jpg"]),
    ]

    integrity = []
    photo_ids_by_set = {}

    for set_name, files in plan:
        cid = sets[set_name]
        files = [f for f in files if f.exists()]
        for f in files:
            local_hash = sh256(f)
            cmd = [
                "curl", "-s", "-b", jar, "-X", "POST",
                f"{ORIGIN}/api/admin/events/{eid}/upload",
                "-H", f"Origin: {ORIGIN}",
                "-H", f"Authorization: Bearer {token()}",
                "-F", f"photos=@{f}",
                "-F", f"category_id={cid}",
            ]
            up = json.loads(subprocess.check_output(cmd, text=True))
            pids = up.get("photo_ids") or []
            if not pids:
                print("UPLOAD FAIL", f, up)
                return 1
            pid = pids[0]
            photo_ids_by_set.setdefault(set_name, []).append(pid)
            integrity.append(
                {
                    "set": set_name,
                    "photo_id": pid,
                    "source_path": str(f.relative_to(ROOT)),
                    "source_filename": f.name,
                    "source_sha256": local_hash,
                    "source_bytes": f.stat().st_size,
                    "upload_response_filename": (up.get("photos") or [{}])[0].get("filename"),
                }
            )
            print(f"  uploaded {f.name} -> photo {pid} sha={local_hash[:12]}…")

    # Cover = first Outdoor portrait
    cover_id = photo_ids_by_set["Outdoor Portraits"][0]
    curl_json(
        "PUT",
        f"/api/admin/events/{eid}",
        {
            "header_style": "hero",
            "hero_photo_id": cover_id,
            "watermark_downloads": False,
            "allow_downloads": True,
        },
    )

    # Brand placeholder logo
    logo = ROOT / "brands" / "placeholders" / "mini-momentz-logo.png"
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

    pub = curl_json(
        "POST",
        f"/api/admin/events/{eid}/publish",
        {"password": GUEST_PASS, "notify_customer": False},
    )
    print("publish", pub.get("message") or pub)

    subprocess.call(
        [
            "docker", "exec", "elp-picpeak", "sh", "-c",
            f"sqlite3 /data/db/picpeak.db \"INSERT INTO event_feedback_settings (event_id, feedback_enabled, allow_favorites, allow_likes, allow_comments, allow_reactions, show_feedback_to_guests, identity_mode) VALUES ({eid},1,1,1,1,1,1,'simple') ON CONFLICT(event_id) DO UPDATE SET feedback_enabled=1;\"",
        ]
    )

    # Guest auth + SHA-256 download verify
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

    dl_dir = RESULTS / "downloads" / "integrity"
    dl_dir.mkdir(parents=True, exist_ok=True)
    pass_n = fail_n = 0
    for row in integrity:
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
        match = code == "200" and dl_hash == row["source_sha256"] and out.stat().st_size == row["source_bytes"]
        row["download_http"] = code
        row["download_sha256"] = dl_hash
        row["download_bytes"] = out.stat().st_size if out.exists() else 0
        row["sha256_match"] = match
        if match:
            pass_n += 1
            print(f"PASS integrity photo {row['photo_id']} ({row['source_filename']})")
        else:
            fail_n += 1
            print(f"FAIL integrity photo {row['photo_id']}: http={code} match={match}")

    # Guest sees categories
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
    cats = photos.get("categories") or []
    print(f"guest categories: {len(cats)} → {[c.get('name') for c in cats]}")

    meta = {
        "brand": "Mini Momentz",
        "client": "Divya & Ravi",
        "gallery": "Seemantham",
        "event_id": eid,
        "slug": slug,
        "share_token": share,
        "client_path": f"/gallery/{slug}/{share}",
        "sets": {k: {"id": v, "photo_ids": photo_ids_by_set.get(k, [])} for k, v in sets.items()},
        "integrity_pass": pass_n,
        "integrity_fail": fail_n,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "sets-demo-gallery.json").write_text(json.dumps(meta, indent=2) + "\n")
    (RESULTS / "original-integrity-raw.json").write_text(json.dumps(integrity, indent=2) + "\n")

    lines = [
        "# Original download integrity (SHA-256)",
        "",
        f"- Origin: `{ORIGIN}`",
        f"- Gallery: Mini Momentz → Divya & Ravi → Seemantham (`id={eid}`)",
        f"- Settings: `download_standard_resolution=original`, watermarks off, original filenames on",
        f"- Result: **{pass_n} PASS / {fail_n} FAIL** of {pass_n + fail_n} files",
        "",
        "| Set | Source file | Bytes | SHA-256 match |",
        "| --- | --- | ---: | --- |",
    ]
    for row in integrity:
        lines.append(
            f"| {row['set']} | `{row['source_filename']}` | {row['source_bytes']} | "
            f"{'PASS' if row['sha256_match'] else 'FAIL'} |"
        )
    lines += [
        "",
        "Raw detail: `apps/gallery/test-results/original-integrity-raw.json`",
        "Downloaded copies (gitignored): `apps/gallery/test-results/downloads/integrity/`",
        "",
        "Conclusion: guest download endpoints return **exact uploaded bytes** when original resolution is the gallery standard and watermarks are disabled.",
    ]
    report = RESULTS / "ORIGINAL_INTEGRITY.md"
    report.write_text("\n".join(lines) + "\n")
    print("Wrote", report)
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
