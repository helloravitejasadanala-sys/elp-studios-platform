"""Shared ELP Studios helpers — brands, share text, PicPeak setting payloads.

No I/O to Docker volumes. Safe to import from apply scripts and tests.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY_DIR = Path(__file__).resolve().parent
BRANDS_DIR = Path(os.environ.get("ELP_BRANDS_DIR", REPO_ROOT / "brands"))
STYLES_DIR = Path(os.environ.get("ELP_STYLES_DIR", REPO_ROOT / "styles"))

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
