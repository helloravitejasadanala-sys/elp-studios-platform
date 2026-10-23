# PicPeak capabilities vs ELP product model

Verification against PicPeak docs (2026-10-23) and `picpeak/aio:stable`. Prefer configure/extend; do not fork the image.

| Need | PicPeak | Status |
| --- | --- | --- |
| Video upload (MP4/MOV) | Native. Default allowed types **exclude** video; add `mp4,mov,webm` | **Configured** via `apply-platform-settings.py` |
| Mixed galleries + player | Native HTML5 player; FFmpeg poster from ~1s | **Native** |
| Photos / Videos filters | Admin Media tab + `media_type` filter (beta). Guest gallery is mixed | **Console + admin**; guest type-tabs not a stable API |
| Upload progress / errors | Native admin uploader + Studio Console XHR/chunked | **Both** |
| No recompression of originals | Downloads use stored file when resolution=original; transcode copies are **beta** and off | **Configured** |
| Optional client email | Event Defaults `event_require_customer_email` | **Configured** — no fake emails |
| WhatsApp share | Not native (footer WhatsApp URL is studio contact only) | **Studio Console** |
| Tabbed create form | Native form is one page (beta has cards, not our tabs) | **Studio Console**; PicPeak Admin unchanged |
| Three brands | One global Branding page; per-event logo + CSS | **Per-event** + console selector |
| PicPeak attribution | `hide_powered_by` left off | **Retained** |
| Storage location | Named volume `elp-picpeak-data` → `/data` | **Windows Docker**, not NAS |
| Dashboard ~763 GB | `statfs` of container disk (WSL2 VHD / host drive) | **Documented** |
| Synology | Not in compose | **Plan only** |

## Genuine limitations (do not fake)

1. **We cannot patch PicPeak’s upload `<input accept>` inside the image.** Enabling Allowed File Types is the supported fix; the native picker then lists videos.
2. **PicPeak has one global company branding record.** Client galleries get the selected studio via per-event logo + CSS template, not three separate PicPeak instances.
3. **Full-day / partial-day** is not a PicPeak field. Stored in an HTML comment in the welcome message for ELP (`elp-duration:`).
4. **`aio:stable` does not transcode HEVC/MOV for every browser.** Prefer H.264 MP4. Downloads remain original bytes.
5. **Katha Films has no genuine logo in this repo.** Placeholder only.

## Pre-production testing gaps

- Live MP4 on the owner’s Windows Docker (this agent has no Docker daemon)
- Cross-browser MOV playback
- Real photography hero contrast
- NAS health (blocked until storage pool is healthy)
