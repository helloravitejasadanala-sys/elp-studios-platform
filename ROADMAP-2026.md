# ELP Studios — 2026 roadmap

Last updated: 2026-10-24.

This is the current plan. It supersedes `IMPLEMENTED.md` and `GAPS.md` for *what we do next*. Those files stay as a snapshot of the Phase 2 work.

**Decision:** the official PicPeak all-in-one image (`picpeak/aio:stable`) is the permanent client gallery. We will not build another gallery UI, replace PicPeak Admin, or fork PicPeak.

**Brands:** Mini Momentz, Katha Films, Tattva Weddings.

**Goal:** a reliable, affordable photography and video production system that reduces manual work.

This repository does **not** deploy or change the live Windows PicPeak service. Volume `elp-picpeak-data` stays untouched.

---

## How this audit was graded

A feature is **working** only if it has run against a real PicPeak (owner Windows Docker, smoke script, or SHA-256 demo). Passing a mock unit test is **not** enough.

| Grade | Meaning |
| --- | --- |
| **Working** | Proven on a live PicPeak or committed smoke/integrity run |
| **Configured** | Scripts/docs exist; owner still has to apply them on the live box |
| **Partial** | Built in this repo, but not proven live, or blocked by a known bug |
| **Planned** | Written down only |
| **Stub** | Folder or README, no product |
| **Cancelled** | We will stop building it |

This cloud environment has **no Docker daemon** and **no NAS access**. Live Windows state is taken from committed test results (2026-10-23) and owner reports (~126 photos still in the volume).

---

## Progress report

### Client galleries (PicPeak)

| Item | Grade | Evidence / caveat |
| --- | --- | --- |
| `picpeak/aio:stable` on Windows Docker Desktop | **Working** | Compose in `apps/gallery/docker-compose.yml`; Admin at `:3000` |
| Named volume `elp-picpeak-data` → `/data` | **Working** | Survives `docker compose down` *without* `-v` |
| Admin login, create event, upload, publish, guest password, favourites, ZIP download | **Working** | `apps/gallery/test-results/SMOKE_TEST_RESULTS.md` (15/15, 2026-10-23) |
| Original-byte guest downloads | **Working** | `STYLES_ORIGINAL_INTEGRITY.md` 12/12; `ORIGINAL_INTEGRITY.md` 7/7 |
| Video in galleries (H.264 MP4) | **Configured** | Native player after Allowed File Types include `mp4,mov,webm`. Demo clip SHA-256 exists. **Live MP4 on the owner PC was not re-checked in this audit.** |
| Optional client email | **Configured** | `apply-platform-settings.py` / Event Defaults. No fake emails. |
| Three CSS styles (slots 1–3) | **Working** (demo) | `styles/wedding-editorial`, `modern-story`, `cinematic-event` |
| Per-event brand (logo + CSS) | **Partial** | Mini + Tattva genuine logos; **Katha is a placeholder** |
| Sets (albums) | **Working** | PicPeak categories with `is_folder: true`; seed script |
| Storage numbers in PicPeak Admin | **Working** | System Status / `storage/info`. ~763 GB is WSL2 disk, not NAS. |
| ELP 70/85/95% alerts + photo/video split | **Partial** | `storage-report.py` works against a live API when run on the owner PC. Studio Console Storage tab is being discontinued. |
| PicPeak in-app Backup & Restore | **Configured, unused** | Default **off**. aio writes `/data/backup` on the **same** volume — not an independent copy. |
| Whole-volume tar of `/data` | **Documented, untested** | Example in `docs/storage.md`. **No restore drill is recorded.** |
| HTTPS / Tunnel / `FRONTEND_URL` | **Planned** | Demo is HTTP `localhost:3000` |
| SMTP client email | **Not started** | Console used `mailto:` only |
| Guest Photos/Videos tabs | **Won't fake** | Not a stable PicPeak public API. Mixed galleries still play. |
| Browser transcode / HLS | **Off** | Beta only. Stay off on `aio:stable` so originals are not recompressed. |

### Studio Console (`:3080`) — discontinued

Built in PR #2 as a companion (tabbed create, brand picker, WhatsApp copy, storage page). It does not store media and does not mount `elp-picpeak-data`.

| Item | Grade | Notes |
| --- | --- | --- |
| Tabbed create + WhatsApp + brand picker | **Partial** | Code exists; live login was broken |
| Docker crash `elp_lib` `parents[2]` | **Broken on `main`** | Fixed only on open PR #3 |
| Cookie session (`admin_token` HttpOnly) | **Broken on `main`** | Fixed only on open PR #4 |
| Doubled path `POST /api/api/auth/admin/login` → 401 then 429 | **Broken on `main`** | Fixed only on open PR #5. PicPeak Admin at `:3000/admin` was fine with the same password. |

**Decision:** stop developing the Console. Do not merge PRs #3–#5 unless you still need `:3080` this week. Keep the code in git for reference. Create events, upload, and share from **PicPeak Admin**. Brand WhatsApp wording stays in `brands/*/brand.json` for copy-paste.

Keep these scripts (they talk to PicPeak Admin APIs, not the Console):

- `apps/gallery/scripts/apply-platform-settings.py`
- `apps/gallery/scripts/storage-report.py`
- `apps/gallery/scripts/verify-storage.ps1`

### Editor workspace

| Item | Grade | Notes |
| --- | --- | --- |
| `apps/editor/` | **Stub** | README + `package.json` that prints “not wired yet”. No UI, no API, no NAS. |
| Synology Drive / Tailscale | **Stub** | Mentioned only. Agents must not connect to the NAS. |
| Lightroom / Premiere integration | **None** | No code. Editors already use their own apps. |
| TrustOS (`trustos-pilot`) | **Out of scope** | Separate repo. Do not merge. |

### Storage, NAS, backup

| Item | Grade | Notes |
| --- | --- | --- |
| Windows Docker volume | **Working** | Live galleries live here today |
| Synology hosting | **Planned, blocked** | Pool previously degraded or missing. See `NAS-ARCHITECTURE.md` |
| Event-based NAS folders | **Planned** | Not created |
| PicPeak External Media (`/external-media:ro`) | **Planned** | Official feature. Not wired in this compose. |
| Automated transfer + checksums | **Planned** | No script |
| Independent `/data` backup + tested restore | **Not done** | Highest-priority real work after this plan is approved |
| Off-site NAS backup | **Unknown** | Owner question |

### Automation and AI

| Item | Grade | Notes |
| --- | --- | --- |
| Demo / settings / smoke scripts | **Working** (when stack is up) | No cron, no NAS jobs |
| AI culling, blur, closed-eye, transcription, proxies | **None** | See optional tools below. Do not alter faces or client photographs. |
| PicPeak People / `picpeak/ml` | **Unavailable on aio** | Face grouping needs the multi-container stack. We stay on `aio:stable`. |

---

## What we keep

1. **PicPeak Admin** at http://localhost:3000/admin — create, upload, publish, share, archive.
2. Volume **`elp-picpeak-data`** — never delete, recreate, or `docker compose down -v`.
3. Brand + style files (`brands/`, `styles/`) and `apply-platform-settings.py`.
4. Read-only storage CLI (`storage-report.py`, `verify-storage.ps1`).
5. Safety docs already in `docs/storage.md` and `docs/storage-and-costs.md`.

## What we cancel

| Cancelled | Why |
| --- | --- |
| Studio Console product | Duplicate UI. Login is broken on `main`. PicPeak Admin is the gallery UI. |
| Custom gallery interface / PicPeak fork | Official `aio:stable` is permanent |
| Custom file-transfer app | Use Synology Drive + VPN first (`EDITOR-WORKFLOW.md`) |
| Custom editor web app (for now) | Prove Drive + a project sheet first. `apps/editor` stays a stub. |
| Beauty AI / face rewrite / auto-retouch | Out of scope. Do not modify client photographs. |
| Enabling PicPeak backup onto the same `/data` volume | Not an independent copy |

Open Console PRs (#3 path crash, #4 cookie login, #5 `/api/api` join) should be **closed or parked** after you confirm you will stop using `:3080`.

---

## Revised roadmap (implement one small stage after approval)

Do not start these until you approve this plan. Each stage is a separate change. Rollback is in `SAFE-MIGRATION-PLAN.md`.

| Stage | Work | Touches live PicPeak? |
| --- | --- | --- |
| **0** | This planning PR | No |
| **1** | First real `/data` backup + restore drill on a **spare** volume/port | Read-only helper container only. Never restore over live. |
| **2** | NAS health check (read-only). No copy, no Container Manager | No |
| **3** | Create empty event-folder shares **after** the pool is Healthy | No |
| **4** | Synology Drive + photo/video editor accounts and ACLs | No |
| **5** | Optional: spare PicPeak + read-only External Media (approved JPEGs only) | Spare instance only |
| **6** | Optional: move gallery hosting to the NAS — only after a tested restore and healthy pool | Copy first, cut over last |

Optional AI (folder scripts, ffmpeg proxies, local Whisper, blur flags) comes **after** Stage 1. Nothing that rewrites pixels.

---

## Optional AI / automation (evaluate later)

Priorities: local processing, privacy, low cost, low maintenance. Check the licence before any commercial use.

| Need | First choice | Licence | Notes |
| --- | --- | --- | --- |
| Project folders | PowerShell / Synology Drive template | — | No AI |
| Proxies | **ffmpeg** H.264 | LGPL (use a documented build) | Local. Do not replace masters. |
| Transcripts / subs | **whisper.cpp** | MIT | Local. Do not upload client audio to a cloud API. |
| Duplicates | **dupeGuru** or PicPeak’s own upload duplicate check | GPL-3 / PicPeak | Flag only; a person decides. |
| Soft / blurry stills | Small **OpenCV** Laplacian script | Apache-2.0 | Flag only. Do not auto-delete. |
| Photo culling | Editor’s existing tool (Lightroom, FastRawViewer, Photo Mechanic) | Commercial, local | Do not send client RAWs to a cloud culling SaaS without a written licence + privacy review. |
| Closed-eye detect | **Defer** | — | Needs face landmarks (GDPR Art. 9 in the UK/EU). Not needed to start. |
| Backup / delivery mail | Hyper Backup email; PicPeak `backup_email_on_failure` later | — | Only after a real off-disk destination exists. |
| People albums | PicPeak `picpeak/ml` | MIT models | **Not on `aio:stable`.** Do not switch stacks just for this. |

**Do not use:** beauty filters, face swap, generative fill, or any tool that rewrites a client’s face or body.

---

## Planning documents

| File | Contents |
| --- | --- |
| `NAS-ARCHITECTURE.md` | Folders, network, backups, External Media |
| `EDITOR-WORKFLOW.md` | Photo/video editor process on Drive |
| `SAFE-MIGRATION-PLAN.md` | Phases and rollback |
| `QUESTIONS.md` | Short list we need you to answer |

Approve the plan, answer `QUESTIONS.md`, then we implement **Stage 1 only**.
