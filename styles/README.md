# Gallery styles (config-driven)

Two visual **styles**, separate from brand identity and from PicPeak app logic.

| Style | Key | Brand (demo) | Owner colours |
| --- | --- | --- | --- |
| **Wedding Editorial** | `wedding-editorial` | Tattva Weddings | Soft Ivory `#F8F6F3`, Deep Crimson `#AB202C`, Plum `#461345`, … |
| **Modern Story** | `modern-story` | Mini Momentz | Teal `#8CCAC6`, Dark Teal `#578884`, Terracotta `#D36727`, … |
| **Cinematic Event** | `cinematic-event` | Katha Films | Warm paper, ink, gold `#C49A6C` (existing Katha accent; placeholder logo) |

Brand specs image (Project store): `media/brand-guidelines/mini-momentz-tattva-brand-specs.jpg`

Each folder has:

- `style.json` — id, intended fonts + **documented fallbacks**, owner colour tokens
- `gallery.css` — PicPeak custom CSS template (tokens only; no app fork)

## Fonts (important)

| Intended | Status |
| --- | --- |
| Futura Now Regular/Bold | **Not shipped** — no licensed files; geometric system + Montserrat CDN stand-in |
| Peach Blossom | **Skipped** until owner supplies |
| Bizantheum | **Not shipped** — do not extract from PDF; Cormorant Garamond stand-in |
| Canela Trial Light | **Not embedded** (trial license); serif fallback until licensed |
| Poppins Light | Google Fonts CDN (license-safe) |

Do **not** pirate fonts or invent official logos. Macro = minimal spacing/nav inspiration only — do not copy Macro branding.

Assign a style via PicPeak CSS template (Admin or `scripts/seed-styles-demo.py`). Change tokens here and re-apply — **no app rebuild**.
