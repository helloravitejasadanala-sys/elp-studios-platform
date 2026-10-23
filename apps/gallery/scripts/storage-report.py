#!/usr/bin/env python3
"""Read-only storage & cost report for the existing ELP PicPeak volume.

Never archives, deletes, prunes volumes, enables backups, or calls paid APIs.

    python scripts/storage-report.py
    python scripts/storage-report.py --json
    python scripts/storage-report.py --skip-docker --skip-photos
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elp_lib import (  # noqa: E402
    STORAGE_VOLUME_NAME,
    build_storage_report,
    format_bytes,
    load_dotenv,
)


class PicPeakRead:
    def __init__(self, origin: str):
        self.origin = origin.rstrip("/")
        self.cookie = ""
        self.token = ""

    def request(self, method: str, path: str, data=None) -> tuple[int, object]:
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
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                cookie = resp.headers.get("Set-Cookie")
                if cookie:
                    self.cookie = cookie.split(";", 1)[0]
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {"error": str(exc)}
            except json.JSONDecodeError:
                parsed = {"error": raw or str(exc)}
            return exc.code, parsed
        except urllib.error.URLError as exc:
            return 502, {"error": str(exc.reason)}

    def login(self, username: str, password: str) -> dict:
        code, body = self.request(
            "POST", "/api/auth/admin/login", {"username": username, "password": password}
        )
        if code >= 400 or not isinstance(body, dict) or "user" not in body:
            raise SystemExit(f"Admin login failed (HTTP {code}): {body}")
        user = body.get("user") or {}
        if body.get("token"):
            self.token = body["token"]
        elif user.get("token"):
            self.token = user["token"]
        return body


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode, out.strip()


def docker_snapshot() -> dict:
    if not shutil.which("docker"):
        return {"available": False, "reason": "docker CLI not found on this machine"}
    snap: dict = {"available": True, "volume_name": STORAGE_VOLUME_NAME, "commands_were_read_only": True}
    code, volume = _run(["docker", "volume", "inspect", STORAGE_VOLUME_NAME, "--format", "{{json .}}"])
    snap["volume_inspect_ok"] = code == 0
    if code == 0:
        try:
            parsed = json.loads(volume)
            snap["mountpoint"] = parsed.get("Mountpoint")
            snap["driver"] = parsed.get("Driver")
        except json.JSONDecodeError:
            snap["volume_raw"] = volume
    else:
        snap["volume_error"] = volume

    code, df = _run(["docker", "exec", "elp-picpeak", "df", "-k", "/data"])
    snap["df_ok"] = code == 0
    snap["df"] = df
    if code == 0:
        for line in df.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[1].isdigit():
                # df -k: 1K blocks
                snap["df_total_bytes"] = int(parts[1]) * 1024
                snap["df_used_bytes"] = int(parts[2]) * 1024
                snap["df_available_bytes"] = int(parts[3]) * 1024
                break

    code, du = _run(
        [
            "docker",
            "exec",
            "elp-picpeak",
            "sh",
            "-c",
            "du -sk /data /data/storage /data/db /data/backup /data/storage/events /data/storage/thumbnails 2>/dev/null",
        ]
    )
    snap["du_ok"] = code == 0
    snap["du"] = {}
    if code == 0:
        for line in du.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                snap["du"][parts[1]] = int(parts[0]) * 1024
    else:
        snap["du_error"] = du
    return snap


def _events_list(body) -> list:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        return body.get("events") or body.get("data") or []
    return []


def collect_picpeak(origin: str, skip_photos: bool) -> dict:
    load_dotenv()
    user = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        return {"error": "ADMIN_PASSWORD is not set. Copy apps/gallery/.env.example to .env first."}
    api = PicPeakRead(origin)
    api.login(user, password)
    _code, info = api.request("GET", "/api/admin/settings/storage/info")
    _code, settings = api.request("GET", "/api/admin/settings")
    _code, events_body = api.request("GET", "/api/admin/events?page=1&limit=100")
    events = _events_list(events_body)
    backup = {}
    for path in ("/api/admin/backup/config", "/api/admin/backup/status", "/api/admin/backup"):
        code, body = api.request("GET", path)
        if code < 400 and isinstance(body, dict) and "error" not in body:
            backup = body
            backup.setdefault("_endpoint", path)
            break
    photos_by_event: dict = {}
    if not skip_photos:
        for event in events[:40]:
            eid = event.get("id")
            if eid is None:
                continue
            code, body = api.request("GET", f"/api/admin/photos/{eid}/photos")
            photos = []
            if isinstance(body, dict):
                photos = body.get("photos") or body.get("data") or []
            elif isinstance(body, list):
                photos = body
            if code < 400:
                photos_by_event[eid] = photos
    return {
        "info": info if isinstance(info, dict) else {},
        "settings": settings if isinstance(settings, dict) else {},
        "events": events,
        "backup": backup,
        "photos_by_event": photos_by_event,
    }


def print_human(report: dict) -> None:
    usage = report["usage"]
    alert = report["alert"]
    print("ELP storage & cost report (read-only)")
    print("Never run: docker compose down -v")
    print(f"Volume: {report['volume_name']}")
    print(f"Alert: {alert['title']} ({alert.get('percent')}% used)")
    print(f"  {alert['advice']}")
    print(
        "Used:",
        format_bytes(usage.get("total_used")),
        " / total",
        format_bytes(usage.get("disk_total")),
        " / free",
        format_bytes(usage.get("disk_available")),
    )
    print("Measurement:", usage.get("storage_measurement") or "picpeak storage/info")
    print(report["capacity_note"])
    docker = report.get("docker") or {}
    if docker.get("available"):
        print("Docker df /data:", format_bytes(docker.get("df_used_bytes")), "used,", format_bytes(docker.get("df_available_bytes")), "free")
        for path, size in (docker.get("du") or {}).items():
            print(f"  du {path}: {format_bytes(size)}")
    elif docker:
        print("Docker inspect skipped:", docker.get("reason") or docker.get("volume_error") or "unavailable")
    print("\nPer-event (catalogued originals; photo/video split from media list when available):")
    for row in report.get("events") or []:
        split = ""
        if row.get("has_media_split"):
            split = f"  photos {format_bytes(row['photo_bytes'])} ({row['photo_count']})  videos {format_bytes(row['video_bytes'])} ({row['video_count']})"
        print(f"  {row.get('event_name')}  {format_bytes(row.get('total_bytes'))}{split}")
    rem = report.get("remaining") or {}
    print("\nRemaining estimate:", rem.get("note") or rem.get("status"))
    bak = report.get("backup") or {}
    print(
        "\nPicPeak backup enabled:",
        bak.get("enabled"),
        " destination:",
        bak.get("destination_type") or "(none)",
        " last:",
        bak.get("last_run") or "never",
    )
    print("Backup note:", bak.get("note"))
    print("\nCost categories (nothing in this report is a paid commitment):")
    for cat in report.get("cost_categories") or []:
        print(f"  - {cat['label']}: {cat['summary']}")
    print("\nTechnical limits:")
    for item in report.get("technical_limits") or []:
        print(f"  - {item['label']}: {item['value']}")
    print("\nArchive/delete stays in PicPeak Admin with its own confirmations.")
    print("This script did not delete data or enable S3/SMTP/Tunnel.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default=os.environ.get("ORIGIN", "http://127.0.0.1:3000"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-docker", action="store_true")
    parser.add_argument("--skip-photos", action="store_true")
    args = parser.parse_args()

    docker = None if args.skip_docker else docker_snapshot()
    picpeak: dict = {}
    try:
        picpeak = collect_picpeak(args.origin, skip_photos=args.skip_photos)
    except SystemExit as exc:
        picpeak = {"error": str(exc)}
    if picpeak.get("error") and not docker:
        print(picpeak["error"], file=sys.stderr)
        return 1
    if picpeak.get("error"):
        print("PicPeak API skipped:", picpeak["error"], file=sys.stderr)

    report = build_storage_report(
        info=picpeak.get("info") or {},
        events=picpeak.get("events") or [],
        photos_by_event=picpeak.get("photos_by_event") or {},
        settings=picpeak.get("settings") or {},
        backup=picpeak.get("backup") or {},
        docker=docker,
    )
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
