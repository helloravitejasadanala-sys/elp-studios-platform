"""Shared ELP Studios helpers — brands, share text, PicPeak setting payloads.

No I/O to Docker volumes. Safe to import from apply scripts and tests.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote


def resolve_repo_root(file_path: Path | None = None) -> Path:
    """Repo root in git; filesystem root in the aio companion container.

    Host layout: ``<root>/apps/gallery/elp_lib.py`` (parents[2] is the root).
    Docker layout: ``/gallery/elp_lib.py`` — only ``/gallery`` and ``/`` exist,
    so ``Path.parents[2]`` raises ``IndexError``. Walk up instead, and honour
    ``ELP_REPO_ROOT`` / ``ELP_BRANDS_DIR`` / ``ELP_STYLES_DIR``.
    """
    override = os.environ.get("ELP_REPO_ROOT")
    if override:
        return Path(override)
    start = (file_path or Path(__file__)).resolve()
    if start.is_file() or start.suffix.lower() == ".py":
        start = start.parent
    for candidate in (start, *start.parents):
        has_brands = (candidate / "brands").is_dir()
        has_gallery = (candidate / "apps" / "gallery").is_dir()
        has_styles = (candidate / "styles").is_dir()
        if has_brands and (has_gallery or has_styles):
            return candidate
    return start


REPO_ROOT = resolve_repo_root()
GALLERY_DIR = Path(__file__).resolve().parent
BRANDS_DIR = Path(os.environ.get("ELP_BRANDS_DIR", REPO_ROOT / "brands"))
STYLES_DIR = Path(os.environ.get("ELP_STYLES_DIR", REPO_ROOT / "styles"))

# PicPeak aio:stable admin session cookie. The login JSON has `user` only;
# the JWT is Set-Cookie: admin_token=…; HttpOnly; Path=/.
ADMIN_COOKIE_NAME = "admin_token"
PICPEAK_LOGIN_PATH = "/api/auth/admin/login"
PICPEAK_LOGOUT_PATH = "/api/auth/logout"
PICPEAK_SESSION_PATH = "/api/auth/session"


def set_cookie_values(headers) -> list[str]:
    """All Set-Cookie values from an HTTP header map (urllib / http.client)."""
    if headers is None:
        return []
    getter = getattr(headers, "get_all", None)
    if callable(getter):
        values = getter("Set-Cookie") or getter("set-cookie") or []
        return [v for v in values if v]
    one = headers.get("Set-Cookie") or headers.get("set-cookie")
    return [one] if one else []


def rewrite_picpeak_cookie_for_proxy(header: str) -> str:
    """Forward PicPeak cookies onto the Studio Console origin (localhost:3080).

    Drop Domain (must not stay ``picpeak``) and Secure (console is HTTP on :3080).
    Keep HttpOnly and force Path=/ so /pp requests receive admin_token.
    """
    raw = (header or "").strip()
    if not raw:
        return raw
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    kept = [parts[0]]
    saw_path = False
    for attr in parts[1:]:
        key = attr.split("=", 1)[0].strip().lower()
        if key in {"domain", "secure"}:
            continue
        if key == "path":
            kept.append("Path=/")
            saw_path = True
            continue
        kept.append(attr)
    if not saw_path:
        kept.append("Path=/")
    return "; ".join(kept)


def admin_token_from_set_cookie(headers_or_values) -> str | None:
    """Read the PicPeak JWT from Set-Cookie. Does not invent a token."""
    if isinstance(headers_or_values, (list, tuple)):
        values = list(headers_or_values)
    else:
        values = set_cookie_values(headers_or_values)
    prefix = ADMIN_COOKIE_NAME + "="
    for raw in values:
        first = raw.split(";", 1)[0].strip()
        if first.startswith(prefix):
            token = first[len(prefix) :]
            if token and token.lower() not in {"deleted", '""', "''"}:
                return token
    return None


def session_from_picpeak_login(body, set_cookie=None) -> dict:
    """Interpret aio:stable admin login. Never synthesises a JWT.

    Stable body: ``{"user": {...}}`` plus ``Set-Cookie: admin_token=``.
    Older bodies may still include ``token``. MFA returns ``mfaRequired``.
    """
    data = body if isinstance(body, dict) else {}
    cookies = set_cookie if isinstance(set_cookie, (list, tuple)) else set_cookie_values(set_cookie)
    cookie_token = admin_token_from_set_cookie(cookies)
    json_token = data.get("token") if isinstance(data.get("token"), str) and data.get("token") else None
    nested = data.get("user") if isinstance(data.get("user"), dict) else {}
    if not json_token:
        nested_token = nested.get("token")
        json_token = nested_token if isinstance(nested_token, str) and nested_token else None
    token = cookie_token or json_token
    if data.get("mfaRequired"):
        return {"ok": False, "reason": "mfa", "user": None, "token": None, "cookie_session": False}
    user = data.get("user") if isinstance(data.get("user"), dict) else None
    if not user:
        return {"ok": False, "reason": "no_session", "user": None, "token": None, "cookie_session": False}
    return {
        "ok": True,
        "reason": None,
        "user": user,
        "token": token,
        "cookie_session": bool(cookie_token),
    }

ALLOWED_FILE_TYPES = "jpg,jpeg,png,webp,gif,heic,mp4,m4v,mov,webm"
# PicPeak default photo cap is 50 MB; videos have a separate cap.
MAX_PHOTO_MB = 50
MAX_VIDEO_MB = 500

EVENT_TYPES = [
    {"name": "Wedding", "slug_prefix": "wedding", "emoji": "💍"},
    {"name": "Engagement", "slug_prefix": "engagement", "emoji": "🤍"},
    {"name": "Birthday", "slug_prefix": "birthday", "emoji": "🎂"},
    {"name": "Maternity", "slug_prefix": "maternity", "emoji": "🌙"},
    {"name": "Newborn", "slug_prefix": "newborn", "emoji": "🍼"},
    {"name": "Baby Shower", "slug_prefix": "baby-shower", "emoji": "🎀"},
    {"name": "Cultural Event", "slug_prefix": "cultural-event", "emoji": "🎬"},
    {"name": "Corporate", "slug_prefix": "corporate", "emoji": "💼"},
    {"name": "Other", "slug_prefix": "other", "emoji": "📷"},
]

# Built-in PicPeak types must not be deleted; create only missing custom ones.
BUILTIN_EVENT_TYPE_SLUGS = {"wedding", "birthday", "corporate", "family", "other"}

GENERAL_SETTINGS = {
    "general_allowed_file_types": ALLOWED_FILE_TYPES,
    "general_max_file_size_mb": MAX_PHOTO_MB,
    "general_max_video_size_mb": MAX_VIDEO_MB,
    "general_use_original_filenames_for_downloads": True,
    "download_standard_resolution": "original",
    "download_allow_original": True,
    "gallery_show_filter_bar": True,
}

EVENT_DEFAULT_SETTINGS = {
    "event_require_customer_email": False,
    "event_require_customer_name": False,
    "event_require_admin_email": False,
    "event_require_event_date": True,
    "event_require_expiration": False,
    "event_phone_field_enabled": True,
    "event_default_require_password": True,
    "event_default_feedback_enabled": True,
    "event_default_allow_favorites": True,
    "event_default_allow_likes": True,
    "event_default_allow_comments": True,
    "event_default_allow_ratings": True,
}

BRAND_ORDER = ("mini-momentz", "katha-films", "tattva-weddings")

DEFAULT_SHARE_BODY = (
    "Your photographs are ready! We've put together your gallery so you can "
    "relive all those beautiful moments.\n\n"
    "View your gallery: {link}"
)


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    env_path = path or (GALLERY_DIR / ".env")
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip().strip('"').strip("'")
        loaded[key.strip()] = val
        os.environ.setdefault(key.strip(), val)
    return loaded


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_logo(brand_id: str, brand: dict) -> Path | None:
    logos = brand.get("logos") or {}
    candidates = []
    if logos.get("client_primary"):
        candidates.append(BRANDS_DIR / brand_id / logos["client_primary"])
    if logos.get("legacy_placeholder"):
        candidates.append((BRANDS_DIR / brand_id / logos["legacy_placeholder"]).resolve())
    candidates.append(BRANDS_DIR / "placeholders" / f"{brand_id}-logo.png")
    for path in candidates:
        if path.exists():
            return path
    return None


def load_brands() -> list[dict]:
    brands = []
    for brand_id in BRAND_ORDER:
        path = BRANDS_DIR / brand_id / "brand.json"
        if not path.exists():
            continue
        data = _read_json(path)
        style_id = data.get("default_style")
        style_meta = {}
        if style_id and (STYLES_DIR / style_id / "style.json").exists():
            style_meta = _read_json(STYLES_DIR / style_id / "style.json")
        logo = resolve_logo(brand_id, data)
        brands.append(
            {
                "id": brand_id,
                "display_name": data.get("display_name", brand_id),
                "colours": data.get("colours") or {},
                "welcome": data.get("client_welcome")
                or (data.get("demo_event") or {}).get("welcome")
                or "",
                "event_categories": data.get("event_categories") or [],
                "whatsapp_share_template": data.get("whatsapp_share_template")
                or DEFAULT_SHARE_BODY + "\n\n{brand}",
                "email_subject": data.get("email_subject")
                or "Your {brand} gallery is ready",
                "email_signature": data.get("email_signature") or data.get("display_name", brand_id),
                "default_style": style_id,
                "css_slot": style_meta.get("picpeak_css_slot"),
                "css_template_name": style_meta.get("picpeak_template_name"),
                "logo_web_path": logo_web_path(logo) if logo else None,
                "logo_filename": logo.name if logo else None,
                "has_genuine_logo": bool(logo and "placeholders" not in logo.parts),
            }
        )
    return brands


def logo_web_path(logo: Path) -> str | None:
    try:
        rel = logo.resolve().relative_to(BRANDS_DIR.resolve())
        return f"/brand-assets/{rel.as_posix()}"
    except ValueError:
        return None


def encode_elp_meta(brand_id: str, duration: str | None = None) -> str:
    parts = [f"elp-brand:{brand_id}"]
    if duration:
        parts.append(f"elp-duration:{duration}")
    return "<!--" + " ".join(parts) + "-->"


def parse_elp_meta(welcome: str | None) -> dict:
    text = welcome or ""
    match = re.search(r"<!--\s*(elp-brand:[^>]+)-->", text)
    out = {"brand_id": None, "duration": None, "welcome_visible": text}
    if not match:
        return out
    body = match.group(1)
    brand = re.search(r"elp-brand:([a-z0-9-]+)", body)
    duration = re.search(r"elp-duration:([a-z0-9-]+)", body)
    out["brand_id"] = brand.group(1) if brand else None
    out["duration"] = duration.group(1) if duration else None
    out["welcome_visible"] = (text[: match.start()] + text[match.end() :]).strip()
    return out


def compose_welcome(brand_id: str, welcome: str, duration: str | None = None) -> str:
    visible = (welcome or "").strip()
    return encode_elp_meta(brand_id, duration) + ("\n" + visible if visible else "")


def infer_brand_from_event(event: dict, brands: list[dict] | None = None) -> str | None:
    meta = parse_elp_meta(event.get("welcome_message") or "")
    if meta.get("brand_id"):
        return meta["brand_id"]
    name = (event.get("event_name") or "").lower()
    for brand in brands or load_brands():
        if brand["display_name"].lower() in name:
            return brand["id"]
    return None


def share_message(brand: dict, link: str) -> str:
    template = brand.get("whatsapp_share_template") or DEFAULT_SHARE_BODY + "\n\n{brand}"
    return (
        template.replace("{link}", link)
        .replace("{brand}", brand.get("display_name") or "")
        .strip()
    )


def whatsapp_url(message: str, phone: str | None = None) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    base = f"https://wa.me/{digits}" if digits else "https://wa.me/"
    return f"{base}?text={quote(message)}"


def mailto_url(brand: dict, link: str, to_email: str | None = None) -> str:
    subject = (brand.get("email_subject") or "Your gallery is ready").replace(
        "{brand}", brand.get("display_name") or ""
    )
    body = share_message(brand, link)
    if brand.get("email_signature"):
        body = body.rstrip() + "\n\n" + brand["email_signature"]
    url = f"mailto:{to_email or ''}?subject={quote(subject)}&body={quote(body)}"
    return url


def event_create_payload(
    *,
    brand_id: str,
    event_name: str,
    event_type: str,
    event_date: str | None,
    client_name: str | None,
    client_email: str | None,
    client_phone: str | None,
    admin_email: str | None,
    welcome: str,
    duration: str | None,
    require_password: bool,
    password: str | None,
    expiration_days: int | None,
    allow_downloads: bool,
    allow_original: bool,
    watermark_downloads: bool,
    feedback_enabled: bool,
    allow_favorites: bool,
    allow_likes: bool,
    allow_comments: bool,
    allow_user_uploads: bool,
    css_template_id: int | None,
    header_style: str = "hero",
    layout: str | None = None,
) -> dict:
    """Build a PicPeak admin create-event body. Omits empty client email."""
    payload = {
        "event_type": event_type or "other",
        "event_name": event_name,
        "require_password": bool(require_password),
        "allow_downloads": bool(allow_downloads),
        "allow_favorites": bool(allow_favorites),
        "allow_likes": bool(allow_likes),
        "allow_comments": bool(allow_comments),
        "feedback_enabled": bool(feedback_enabled),
        "watermark_downloads": bool(watermark_downloads),
        "allow_user_uploads": bool(allow_user_uploads),
        "header_style": header_style,
        "hero_logo_visible": True,
        "hero_logo_size": "medium",
        "hero_logo_position": "center",
        "disable_right_click": False,
        "welcome_message": compose_welcome(brand_id, welcome, duration),
    }
    if event_date:
        payload["event_date"] = event_date
    if client_name:
        payload["customer_name"] = client_name
    if client_email:
        payload["customer_email"] = client_email
    if client_phone:
        payload["customer_phone"] = client_phone[:32]
    if admin_email:
        payload["admin_email"] = admin_email
    if require_password and password:
        payload["password"] = password
    if expiration_days:
        payload["expiration_days"] = int(expiration_days)
    if allow_original:
        payload["download_standard_resolution"] = "original"
    if css_template_id:
        payload["css_template_id"] = css_template_id
    if layout:
        payload["layout"] = layout
    return payload


# --- Storage & cost monitoring (read-only math; never deletes) -----------------

STORAGE_VOLUME_NAME = "elp-picpeak-data"
STORAGE_LOOKBACK_DAYS = 14
STORAGE_ALERT_THRESHOLDS = (
    {
        "percent": 70,
        "level": "watch",
        "title": "Watch (70%)",
        "advice": "Plan archive of delivered galleries and confirm a backup exists off this disk.",
    },
    {
        "percent": 85,
        "level": "warning",
        "title": "Warning (85%)",
        "advice": "Pause large video batches. Archive finished events in PicPeak Admin (zip, then active originals are removed). Do not delete the Docker volume.",
    },
    {
        "percent": 95,
        "level": "critical",
        "title": "Critical (95%)",
        "advice": "Uploads may fail. Free space by archiving in PicPeak, emptying trash, or expanding the disk. Never run docker compose down -v.",
    },
)

VIDEO_SUFFIXES = (".mp4", ".m4v", ".mov", ".webm", ".avi")
PHOTO_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
    ".heif",
    ".dng",
)

TECHNICAL_LIMITS = (
    {
        "id": "photo_upload",
        "label": "Photo upload size",
        "value": "50 MB default (PicPeak range 1–500 MB)",
        "source": "PicPeak General → Max File Size",
    },
    {
        "id": "video_upload",
        "label": "Video upload size",
        "value": "500 MB default (raise in Admin; image/docs cap 10 GB; proxy body limit must match)",
        "source": "PicPeak General → Max Video Size",
    },
    {
        "id": "files_per_upload",
        "label": "Files per upload batch",
        "value": "500 default (1–2000)",
        "source": "PicPeak General → Max Files per Upload",
    },
    {
        "id": "batch_mb",
        "label": "Upload batch request size",
        "value": "95 MB default (lower behind Cloudflare’s ~100 MB body limit)",
        "source": "PicPeak General → Max Upload Batch Size",
    },
    {
        "id": "chunked",
        "label": "Large-file upload",
        "value": "Admin chunked upload, 10 MB chunks (Studio Console uses this above ~40 MB)",
        "source": "PicPeak Photos API",
    },
    {
        "id": "sqlite_writer",
        "label": "Simultaneous uploads",
        "value": "aio:stable uses SQLite — one writer at a time; concurrent uploads queue",
        "source": "PicPeak single-container install",
    },
    {
        "id": "admin_inflight",
        "label": "Admin uploads in flight",
        "value": "Default 16 concurrent requests per admin account, 64 per deployment; staged bytes capped vs free disk",
        "source": "ADMIN_UPLOAD_LIMITS_JSON",
    },
    {
        "id": "video_processing",
        "label": "Video processing",
        "value": "aio:stable extracts a poster ~1s in; browser-playable copies and HLS/adaptive streaming are beta and off — originals are not recompressed",
        "source": "PicPeak Video Support",
    },
    {
        "id": "server_ram",
        "label": "Server performance",
        "value": "4 GB RAM recommended once video is regular; 2 GB hosts should set UPLOAD_PROCESSOR_CONCURRENCY=1",
        "source": "PicPeak system requirements",
    },
    {
        "id": "trash",
        "label": "Trash retention",
        "value": "30 days default; trashed files still occupy disk until purged",
        "source": "PicPeak General",
    },
)

COST_CATEGORIES = (
    {
        "id": "software",
        "label": "Software",
        "committed": False,
        "summary": "PicPeak is open-source and self-hosted (no monthly licence). This Studio Console is local. No software subscription is enabled here.",
    },
    {
        "id": "hosting",
        "label": "Hosting",
        "committed": False,
        "summary": "Current demo runs on the Windows PC Docker volume. Cost is electricity + the disk Docker Desktop uses (WSL2 VHD). Synology NAS hosting is planned only — not connected.",
    },
    {
        "id": "backup",
        "label": "Backup",
        "committed": False,
        "summary": "PicPeak built-in backup defaults to off. A local tar of elp-picpeak-data is free but is not independent if it stays on the same disk. Off-site copies (extra disk, Synology Hyper Backup, object storage) cost extra only if you choose them later.",
    },
    {
        "id": "third_party",
        "label": "Optional third-party",
        "committed": False,
        "summary": "Not enabled: SMTP email, Cloudflare Tunnel/domain, S3/R2/B2 storage, paid analytics, paid WhatsApp Business API. wa.me share links are free. This repo does not create those accounts.",
    },
)

ARCHIVE_POLICY = {
    "console_deletes": False,
    "picpeak_native": True,
    "confirm_with": "gallery name",
    "steps": (
        "Archive is a PicPeak action, not an ELP silent job. Open Admin → the gallery → Archive Gallery (or Events → bulk Archive Selected).",
        "PicPeak writes a zip of originals + feedback, then deletes active originals, thumbnails, hero files and cached watermarks. The public gallery URL stops working.",
        "The zip stays under events/archived/ until you use Delete on Admin → Events → Archives. Restore from that page extracts photos and regenerates thumbnails.",
        "Expiry can auto-archive when expires_at passes. Set expiry only if you want that. Trash (default 30 days) is a separate photo-level recycle bin.",
        "This console never calls archive or delete APIs. Type the gallery name here only to unlock a link into PicPeak Admin.",
    ),
    "never": (
        "docker compose down -v",
        "docker volume rm elp-picpeak-data",
        "Deleting /data from inside the container",
        "Restoring a backup over the live volume without a spare copy",
    ),
}

BACKUP_POLICY = {
    "picpeak_default_enabled": False,
    "aio_local_path": "/data/backup (symlink /backup)",
    "independent": "A backup on the same Docker volume is not a second copy. Keep a tar or Hyper Backup target off this disk.",
    "restore_test": (
        "Copy elp-picpeak-data to a tar while the stack is running (read-only helper container).",
        "Restore that tar into a spare folder or a throwaway volume — never onto the live volume first.",
        "Start a second PicPeak (different port/volume) from the spare copy and open one known gallery.",
        "Confirm jwt.secret came along so share links still verify.",
        "Only then treat the backup as real. PicPeak UI Restore overwrites the live database — practise on a spare instance.",
    ),
    "admin_paths": {
        "backup": "/admin/backup",
        "archives": "/admin/events/archives",
        "system_status": "/admin/settings",
    },
}


def _as_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_timestamp(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def classify_media(filename: str | None = None, mime_type: str | None = None) -> str:
    mime = (mime_type or "").lower()
    name = (filename or "").lower()
    if mime.startswith("video/") or any(name.endswith(ext) for ext in VIDEO_SUFFIXES):
        return "video"
    if mime.startswith("image/") or any(name.endswith(ext) for ext in PHOTO_SUFFIXES):
        return "photo"
    return "other"


def photo_filename(photo: dict) -> str:
    return str(
        photo.get("filename")
        or photo.get("original_filename")
        or photo.get("original_name")
        or photo.get("name")
        or ""
    )


def photo_mime(photo: dict) -> str:
    return str(
        photo.get("mime_type")
        or photo.get("mimetype")
        or photo.get("content_type")
        or photo.get("type")
        or ""
    )


def photo_size_bytes(photo: dict) -> int:
    return _as_int(
        photo.get("size_bytes")
        or photo.get("file_size")
        or photo.get("filesize")
        or photo.get("size")
        or photo.get("bytes")
    )


def photo_uploaded_at(photo: dict) -> datetime | None:
    return parse_timestamp(
        photo.get("created_at")
        or photo.get("uploaded_at")
        or photo.get("createdAt")
        or photo.get("uploadedAt")
        or photo.get("taken_at")
    )


def format_bytes(n) -> str:
    if n is None:
        return "—"
    try:
        value = float(n)
    except (TypeError, ValueError):
        return "—"
    if value < 0:
        return "—"
    units = ("B", "KB", "MB", "GB", "TB")
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    if idx == 0 or value >= 10:
        return f"{int(round(value))} {units[idx]}"
    return f"{value:.1f} {units[idx]}"


def storage_fill_percent(used, capacity) -> float | None:
    used_n = _as_int(used, default=-1)
    cap_n = _as_int(capacity, default=-1)
    if used_n < 0 or cap_n <= 0:
        return None
    return min(999.0, round(100.0 * used_n / cap_n, 1))


def storage_alert_for_percent(percent: float | None) -> dict:
    if percent is None:
        return {
            "level": "unknown",
            "percent": None,
            "threshold": None,
            "title": "Capacity unknown",
            "advice": "PicPeak did not return a usable disk total. Run scripts/verify-storage.ps1 (or .sh) and read docs/storage-and-costs.md.",
        }
    matched = None
    for row in STORAGE_ALERT_THRESHOLDS:
        if percent >= row["percent"]:
            matched = row
    if matched is None:
        return {
            "level": "ok",
            "percent": percent,
            "threshold": None,
            "title": "Storage OK",
            "advice": "Below 70% of reported capacity. Keep backups off this disk anyway.",
        }
    return {
        "level": matched["level"],
        "percent": percent,
        "threshold": matched["percent"],
        "title": matched["title"],
        "advice": matched["advice"],
    }


def estimate_remaining_capacity(
    *,
    available_bytes,
    recent_bytes,
    window_days: int = STORAGE_LOOKBACK_DAYS,
    sample_count: int = 0,
) -> dict:
    available = _as_int(available_bytes, default=-1)
    recent = _as_int(recent_bytes, default=-1)
    days = int(window_days or 0)
    base = {
        "window_days": days,
        "recent_bytes": max(recent, 0) if recent >= 0 else None,
        "available_bytes": available if available >= 0 else None,
        "bytes_per_day": None,
        "days_remaining": None,
        "confidence": "none",
        "status": "unknown",
        "note": "",
    }
    if available < 0:
        base["note"] = "Available disk bytes are missing, so a remaining-capacity estimate cannot be computed."
        return base
    if days <= 0 or recent < 0:
        base["note"] = "Need a lookback window and recent upload totals to estimate remaining capacity."
        return base
    if recent == 0:
        base["status"] = "idle"
        base["confidence"] = "low"
        base["note"] = f"No uploads in the last {days} days. Remaining capacity is the free disk, with no burn-rate."
        return base
    per_day = recent / days
    remaining = available / per_day if per_day else None
    confidence = "high" if sample_count >= 8 else ("medium" if sample_count >= 3 else "low")
    base.update(
        {
            "bytes_per_day": int(round(per_day)),
            "days_remaining": round(remaining, 1) if remaining is not None else None,
            "confidence": confidence,
            "status": "ok",
            "note": (
                f"At the last {days} days’ upload rate, reported free space lasts about "
                f"{int(remaining) if remaining and remaining >= 1 else remaining} day(s). "
                "This is the Docker/WSL2 disk PicPeak can see, not a gallery quota and not Synology."
            ),
        }
    )
    return base


def event_media_usage(photos: list | None) -> dict:
    photo_bytes = video_bytes = other_bytes = 0
    photo_count = video_count = other_count = 0
    dated = []
    for photo in photos or []:
        size = photo_size_bytes(photo)
        kind = classify_media(photo_filename(photo), photo_mime(photo))
        if kind == "video":
            video_bytes += size
            video_count += 1
        elif kind == "photo":
            photo_bytes += size
            photo_count += 1
        else:
            other_bytes += size
            other_count += 1
        uploaded = photo_uploaded_at(photo)
        if uploaded:
            dated.append((uploaded, size))
    return {
        "photo_bytes": photo_bytes,
        "video_bytes": video_bytes,
        "other_bytes": other_bytes,
        "photo_count": photo_count,
        "video_count": video_count,
        "other_count": other_count,
        "total_bytes": photo_bytes + video_bytes + other_bytes,
        "file_count": photo_count + video_count + other_count,
        "dated": dated,
    }


def nested_setting(settings: dict | None, key: str):
    if not isinstance(settings, dict):
        return None
    if key in settings:
        return settings[key]
    for nest in settings.values():
        if isinstance(nest, dict) and key in nest:
            return nest[key]
    return None


def _truthy(value) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def build_storage_report(
    *,
    info: dict | None = None,
    events: list | None = None,
    photos_by_event: dict | None = None,
    settings: dict | None = None,
    backup: dict | None = None,
    docker: dict | None = None,
    now: datetime | None = None,
    lookback_days: int = STORAGE_LOOKBACK_DAYS,
) -> dict:
    """Compose a read-only monitoring snapshot from PicPeak APIs + optional docker inspect.

    Does not archive, delete, enable backups, or call paid services.
    """
    info = info or {}
    events = list(events or [])
    photos_by_event = photos_by_event or {}
    settings = settings or {}
    backup = backup or {}
    now = now or datetime.now(timezone.utc)

    used = _as_int(info.get("total_used"), default=-1)
    disk_total = _as_int(info.get("disk_total"), default=-1)
    disk_available = _as_int(info.get("disk_available"), default=-1)
    if disk_available < 0:
        disk_available = _as_int(info.get("disk_free"), default=-1)
    cataloged = _as_int(info.get("cataloged_bytes"), default=-1)
    soft_limit = _as_int(
        info.get("configured_soft_limit") or info.get("storage_soft_limit") or info.get("storage_limit"),
        default=-1,
    )
    capacity_for_alert = disk_total if disk_total > 0 else (soft_limit if soft_limit > 0 else -1)
    percent = storage_fill_percent(used if used >= 0 else None, capacity_for_alert if capacity_for_alert > 0 else None)
    alert = storage_alert_for_percent(percent)

    catalog_by_id = {}
    for row in info.get("storage_by_event") or []:
        if not isinstance(row, dict):
            continue
        eid = row.get("id") or row.get("event_id")
        if eid is None:
            continue
        catalog_by_id[int(eid)] = {
            "event_id": int(eid),
            "event_name": row.get("event_name") or row.get("name") or "",
            "cataloged_bytes": _as_int(row.get("size") or row.get("size_bytes") or row.get("total")),
        }

    cutoff = now - timedelta(days=lookback_days)
    recent_bytes = 0
    recent_files = 0
    per_event = []
    for event in events:
        eid = event.get("id")
        photos = photos_by_event.get(eid) or photos_by_event.get(str(eid)) or []
        usage = event_media_usage(photos)
        catalog = catalog_by_id.get(int(eid) if eid is not None else -1, {})
        total = usage["total_bytes"] if usage["file_count"] else catalog.get("cataloged_bytes", 0)
        for uploaded, size in usage["dated"]:
            if uploaded >= cutoff:
                recent_bytes += size
                recent_files += 1
        per_event.append(
            {
                "id": eid,
                "event_name": event.get("event_name") or catalog.get("event_name") or "Untitled",
                "status": (
                    "archived"
                    if event.get("is_archived") or event.get("status") == "archived"
                    else "expired"
                    if event.get("expires_at") and parse_timestamp(event.get("expires_at")) and parse_timestamp(event["expires_at"]) < now
                    else "draft"
                    if event.get("is_draft")
                    else "published"
                ),
                "photo_bytes": usage["photo_bytes"],
                "video_bytes": usage["video_bytes"],
                "other_bytes": usage["other_bytes"],
                "photo_count": usage["photo_count"],
                "video_count": usage["video_count"],
                "file_count": usage["file_count"],
                "total_bytes": total,
                "cataloged_bytes": catalog.get("cataloged_bytes"),
                "has_media_split": bool(usage["file_count"]),
            }
        )
    # Include catalog-only events PicPeak returned that were not in the events page.
    seen = {row["id"] for row in per_event}
    for eid, catalog in catalog_by_id.items():
        if eid in seen:
            continue
        per_event.append(
            {
                "id": eid,
                "event_name": catalog["event_name"] or "Untitled",
                "status": "unknown",
                "photo_bytes": 0,
                "video_bytes": 0,
                "other_bytes": 0,
                "photo_count": 0,
                "video_count": 0,
                "file_count": 0,
                "total_bytes": catalog["cataloged_bytes"],
                "cataloged_bytes": catalog["cataloged_bytes"],
                "has_media_split": False,
            }
        )
    per_event.sort(key=lambda row: row.get("total_bytes") or 0, reverse=True)

    remaining = estimate_remaining_capacity(
        available_bytes=disk_available if disk_available >= 0 else None,
        recent_bytes=recent_bytes,
        window_days=lookback_days,
        sample_count=recent_files,
    )
    remaining_vs_soft = None
    if soft_limit > 0 and used >= 0:
        remaining_vs_soft = estimate_remaining_capacity(
            available_bytes=max(soft_limit - used, 0),
            recent_bytes=recent_bytes,
            window_days=lookback_days,
            sample_count=recent_files,
        )

    backup_enabled = _truthy(backup.get("backup_enabled"))
    if backup_enabled is None:
        backup_enabled = _truthy(nested_setting(settings, "backup_enabled"))
    last_run = (
        backup.get("lastBackup")
        or backup.get("last_backup")
        or backup.get("lastRun")
        or backup.get("last_run_at")
    )
    next_run = (
        backup.get("nextBackup")
        or backup.get("next_backup")
        or backup.get("nextScheduledRun")
    )

    return {
        "generated_at": now.isoformat(),
        "volume_name": STORAGE_VOLUME_NAME,
        "destructive": False,
        "paid_services_enabled": False,
        "capacity_note": (
            "disk_total / disk_available come from PicPeak fs.statfs() on /data. "
            "On Docker Desktop for Windows this is usually the WSL2 virtual disk, not Synology and not a gallery quota."
        ),
        "usage": {
            "total_used": used if used >= 0 else None,
            "cataloged_bytes": cataloged if cataloged >= 0 else None,
            "archive_storage": _as_int(info.get("archive_storage"), default=None)
            if info.get("archive_storage") is not None
            else None,
            "disk_total": disk_total if disk_total >= 0 else None,
            "disk_available": disk_available if disk_available >= 0 else None,
            "disk_free": _as_int(info.get("disk_free"), default=-1) if info.get("disk_free") is not None else None,
            "disk_metrics_reliable": bool(info.get("disk_metrics_reliable"))
            if "disk_metrics_reliable" in info
            else disk_total > 0,
            "storage_measurement": info.get("storage_measurement"),
            "storage_breakdown": info.get("storage_breakdown"),
            "storage_partial": bool(info.get("storage_partial")),
            "soft_limit_bytes": soft_limit if soft_limit > 0 else None,
            "soft_limit_configured": bool(info.get("soft_limit_configured") or info.get("configured_soft_limit")),
            "recommended_soft_limit": _as_int(info.get("recommended_soft_limit"), default=-1)
            if info.get("recommended_soft_limit") is not None
            else None,
            "percent_used": percent,
            "fill_basis": "disk_total" if disk_total > 0 else ("soft_limit" if soft_limit > 0 else None),
        },
        "alert": alert,
        "alerts": list(STORAGE_ALERT_THRESHOLDS),
        "events": per_event,
        "remaining": remaining,
        "remaining_vs_soft_limit": remaining_vs_soft,
        "lookback_days": lookback_days,
        "recent_upload_bytes": recent_bytes,
        "recent_upload_files": recent_files,
        "docker": docker,
        "backup": {
            "enabled": backup_enabled,
            "destination_type": backup.get("backup_destination_type")
            or nested_setting(settings, "backup_destination_type"),
            "last_run": last_run,
            "next_run": next_run,
            "include_archived": _truthy(
                backup.get("backup_include_archived")
                if "backup_include_archived" in backup
                else nested_setting(settings, "backup_include_archived")
            ),
            "status_source": "picpeak" if backup else "settings",
            "independent_copy": False if backup_enabled else None,
            "note": BACKUP_POLICY["independent"],
        },
        "limits_live": {
            "max_photo_mb": nested_setting(settings, "general_max_file_size_mb") or MAX_PHOTO_MB,
            "max_video_mb": nested_setting(settings, "general_max_video_size_mb") or MAX_VIDEO_MB,
            "allowed_file_types": nested_setting(settings, "general_allowed_file_types"),
            "max_files_per_upload": nested_setting(settings, "general_max_files_per_upload"),
            "max_batch_mb": nested_setting(settings, "general_max_upload_batch_size_mb"),
            "trash_retention_days": nested_setting(settings, "general_trash_retention_days"),
        },
        "technical_limits": list(TECHNICAL_LIMITS),
        "cost_categories": list(COST_CATEGORIES),
        "archive_policy": ARCHIVE_POLICY,
        "backup_policy": BACKUP_POLICY,
        "picpeak": {
            "storage_info": "/api/admin/settings/storage/info",
            "admin_backup": "/admin/backup",
            "admin_archives": "/admin/events/archives",
            "admin_status": "/admin/settings",
        },
    }
