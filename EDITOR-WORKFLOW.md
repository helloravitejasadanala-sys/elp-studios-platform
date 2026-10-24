# Editor workflow (photo and video)

Use software you already have. **Do not build a custom transfer portal** until Synology Drive and secure remote access have been tried.

`apps/editor/` is a stub (README + a package script that prints “not wired yet”). Leave it that way until Drive + a project sheet is clearly not enough.

PicPeak remains the **client gallery** only. Editors do not need PicPeak Admin. Clients do not need Drive.

---

## Principles

1. Separate **photo** and **video** access.
2. An editor sees **assigned events only**.
3. Masters stay on the NAS (or the photographer’s disk); work files can be local.
4. Review happens with comments and a revision number, not a rewritten original.
5. Studio admin alone marks **approved** and publishes to PicPeak.
6. No beauty AI, face rewrite, or automatic pixel changes.

---

## Roles

| Role | Typical person | Sees | Writes |
| --- | --- | --- | --- |
| Studio admin | You | All events, backups, PicPeak | Brief, assigns, `07-approved`, PicPeak publish |
| Photo editor | e.g. Rajesh | Assigned photo jobs | `01-selects` (if handed), `05-edited`, `06-review` |
| Video editor | Katha / freelance | Assigned video jobs | `02-footage` or proxies, `05-edited`, `06-review` |
| Client | Family / couple | PicPeak gallery link only | Favourites / comments in PicPeak |

DSM groups: `elp-admin`, `elp-photo-editors`, `elp-video-editors`. Per-event ACL **Deny** everyone else. Synology Drive Team Folder permissions follow the shared-folder ACL ([Synology mapping](https://kb.synology.com/en-us/DSM/tutorial/Mapping_ACL_permission_to_Drive)).

Remote editors: **Tailscale** (or another VPN) to Drive. Do not expose DSM or PicPeak Admin to the public internet.

---

## Project lifecycle

```
Booked → Folders created → Brief + refs in
  → Handoff (selects / footage / proxies)
  → In edit → Uploaded to 05-edited
  → In review (comments, rev N)
  → Changes requested → back to In edit
  → Approved → copy/export into 07-approved
  → Delivered (PicPeak published) → Closed
```

Track these fields on every job (spreadsheet or `PROJECT.md`):

- Brand (`mini-momentz` / `katha-films` / `tattva-weddings`)
- Client short name (no extra PII in folder names)
- Event date
- Type (photo / video / both)
- Assignee
- Due date
- Priority (now / this week / later)
- Status (from the list above)
- PicPeak event link (after create)
- Revision (`rev1`, `rev2`, …)

**Tracker v1:** a Synology Office sheet (or a local spreadsheet you already use) plus `PROJECT.md` in the event folder.  
**Tracker v2:** only if v1 fails — a small app in `apps/editor`. Not this quarter unless you ask.

---

## What the editor receives

| Kind | Where | Notes |
| --- | --- | --- |
| Instructions | `00-brief/` | Shot list, colour notes, music, do-not-use list |
| Reference images / clips | `00-brief/refs/` | Mood only. Not client delivery |
| Photo selects | `01-selects/` | JPEG or RAW the photographer already picked. Not the whole card dump unless you intend that |
| Video originals | `02-footage/` | If the file is huge, hand **proxies** in `03-proxies/` and keep originals on the NAS |
| Project file | Local disk | `.lrdata` / Premiere / DaVinci stay off Drive when they are large |

Photographers continue to cull in **Lightroom / FastRawViewer / Photo Mechanic** on their own PC. This repo will not automate Lightroom.

---

## What the editor returns

Upload into `05-edited/revN/` (example: `05-edited/rev1/`).

- Photos: full-resolution JPEG (sRGB unless the brief says otherwise). Do not overwrite selects.
- Video: H.264 MP4 (PicPeak plays this on `aio:stable` without beta transcode). Keep a high-quality master in the same `revN` folder if asked.
- A short `NOTES.txt`: what changed, fonts/music used, anything unfinished.

Admin reviews, writes comments in `06-review/revN.md` (or Drive file comments), and either:

- requests `revN+1`, or
- copies the agreed files into `07-approved/` and ticks **Approved**.

Only `07-approved/` is a PicPeak source later. Editors have **no write** there.

---

## Review, revisions, approval

1. Admin opens `05-edited/revN` on Drive (or a local sync).
2. Comments go in `06-review/revN.md` with file names and timestamps.
3. Editor uploads `revN+1` as a **new folder**. Do not replace `rev1`.
4. Approval is an admin status change + copy into `07-approved`.
5. Delivery is PicPeak: create/open the event, upload (or later External Media scan), set password, send the share link. WhatsApp text can be copied from `brands/<id>/brand.json`.

PicPeak guest favourites remain the **client** proofing tool. Editor revisions stay on Drive.

---

## Isolation (other clients’ files)

| Control | How |
| --- | --- |
| Folder ACL | Event folder granted only to assignee + `elp-admin` |
| Drive share | Private invite, not “internal / everyone on the NAS” |
| PicPeak | Editors do not get Admin. No shared admin password. |
| External Media (later) | SuperAdmin assigns source folders per account. Do not mount the whole `events/` tree if one editor should not see all brands. |
| Local sync | Editor syncs **that event** only, not `elp-studio/` |

If two editors must not see each other’s clients, do not use one world-readable Team Folder.

---

## Proxies and heavy video

Generate proxies **locally** with ffmpeg (see `ROADMAP-2026.md`). Store them in `03-proxies/`. They are disposable; originals in `02-footage/` are the backup target.

PicPeak `aio:stable` External Media will **not** ingest video from a folder. Finished films are uploaded in PicPeak Admin until you deliberately move to beta (not recommended).

---

## Why not a custom app yet

Synology Drive already gives: named users, per-folder ACL, web + desktop sync, comments, no extra hosting cost, and no new password database. A custom uploader would need auth, storage, and audit — and would sit next to a NAS whose pool is not yet trusted.

Build `apps/editor` only if Drive cannot express assignment, due dates, or revision history after you have used it on real jobs.

---

## Mapping to PicPeak (admin only)

| Editor world | PicPeak |
| --- | --- |
| Event folder | One PicPeak event |
| Brand | Per-event logo + CSS slot (Mini / Katha / Tattva) |
| `07-approved` stills | Upload, or External Media reference (JPEG/PNG/WebP) |
| Finished MP4 | Admin upload (stable) |
| Client link | PicPeak share URL + password |
| Client picks | PicPeak favourites |

Do not give editors the PicPeak admin password. Do not put RAW in PicPeak.
