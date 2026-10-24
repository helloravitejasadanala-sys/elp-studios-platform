# Safe migration plan

Phased. Each stage has a rollback. **Nothing in this document is to be run until you approve the plan** and we take **one stage** at a time.

Live service today: Windows Docker Desktop, `elp-picpeak`, volume **`elp-picpeak-data`**, Admin http://localhost:3000/admin.

---

## Hard rules (every stage)

- Do not delete, reset, replace, reformat, or initialise NAS volumes.
- Do not run `docker compose down -v`.
- Do not delete or recreate `elp-picpeak-data`.
- Do not restore a backup over the live volume.
- Do not mount `/data` on SMB/CIFS.
- Do not enable paid backup/S3/SMTP from this repo.
- If unsure, stop. The current gallery stays on Windows.

---

## Stage 0 — Plan (this PR)

**Does:** add planning docs only.  
**Does not:** change compose, containers, or the volume.

Rollback: close the PR. No runtime effect.

---

## Stage 1 — Prove a PicPeak backup (first implementation)

**Goal:** one tar of `/data` that you have **restored on a spare instance**.

1. Confirm `docker volume inspect elp-picpeak-data` and that http://localhost:3000 still opens.
2. Tar with a **read-only** mount to a disk that is **not** the Docker VHD (see `NAS-ARCHITECTURE.md`).
3. Create volume `elp-picpeak-restore-test` (different name).
4. Start a second `picpeak/aio:stable` on port **3001** using only that test volume.
5. Open one known gallery, download one original, confirm login.
6. Stop the test container. Remove **only** `elp-picpeak-restore-test`.
7. Keep the tar. Copy `jwt.secret` to a restricted folder.

**Rollback:** you only added a file and a disposable volume. Live `:3000` was not written.

**Stop if:** tar is smaller than `/data`, `jwt.secret` is missing, or the test gallery does not open.

---

## Stage 2 — NAS health (read-only)

**Goal:** decide whether the Synology may receive copies.

Check in DSM Storage Manager (you, not an agent):

- Pool status is **Healthy** (not degraded, crashed, or missing)
- No uninitiated or failed disks you were not expecting
- Volume free space (plan 3–5× current gallery once video is regular)
- DSM new enough for Drive / Container Manager if you want them later
- Whether Hyper Backup already has a **second** target

**Does not:** create shares, copy `elp-picpeak-data`, or install Docker on the NAS.

**Rollback:** nothing was written.

**Stop if:** any health gate fails. Stay on Windows. Do not “just format and start again”.

---

## Stage 3 — Empty studio folders

**Only if Stage 2 passed.**

Create share `elp-studio` on the **healthy** volume with the tree in `NAS-ARCHITECTURE.md`. Leave it empty of client photos. Set group ACLs.

**Rollback:** delete the new empty share only. Do not touch other volumes.

**Stop if:** DSM asks to initialise, repair, or recreate a pool. Cancel.

---

## Stage 4 — Drive and editor accounts

Enable Synology Drive on `elp-studio`. Create `elp-admin`, `elp-photo-editors`, `elp-video-editors`. Add one test event folder. Invite one photo and one video account. Confirm they cannot see a second dummy event.

Remote: Tailscale (or existing VPN) only.

**Rollback:** disable Drive for those users; remove the test folder. PicPeak unchanged.

---

## Stage 5 — Spare PicPeak + External Media (optional)

**Not the live container.**

1. Run a spare `aio:stable` with its **own** volume.
2. Bind-mount a **copy** of a dummy `07-approved` JPEG folder to `/external-media:ro`.
3. Set `EXTERNAL_MEDIA_ROOT=/external-media`.
4. Create a test event, Reference external folder, import. Confirm originals on disk are untouched (read-only).

**Rollback:** stop spare container and its volume. Live `:3000` and `elp-picpeak-data` stay as they are.

**Do not** add External Media to the live compose until this spare test is written up.

Stable will not import RAW or (on stable) video from that folder.

---

## Stage 6 — Host PicPeak on the NAS (optional, last)

Only after: Stage 1 restore worked, Stage 2 Healthy, Stage 3–4 in use, and you still want the PC off.

1. Fresh tar of live `elp-picpeak-data` (Stage 1 again).
2. On the NAS, a **local** folder or Container Manager volume for `/data` — never an SMB mount.
3. Restore the tar into that folder. Start `picpeak/aio:stable`.
4. Test draft + one real gallery on a NAS LAN URL. Keep Windows PicPeak **running** until you are sure.
5. Only then change DNS / Tunnel. Keep the Windows volume as rollback for weeks.

**Rollback:** point clients back to the Windows container. Do not delete the Windows volume.

**Do not** run this as part of “simplify the platform”. It is a later hosting move.

---

## Studio Console wind-down

| Action | When |
| --- | --- |
| Stop opening http://localhost:3080 | Now (after you approve) |
| Do not merge PRs #3–#5 | After you confirm you will not use the Console |
| Leave `apps/studio-console/` in git | Keep for history |
| `docker compose stop studio-console` | Safe. Does not touch `picpeak` or the volume |
| `docker compose up -d picpeak` | If you ever need to start **only** the gallery |

Do not `docker compose down`.

---

## Rollback cheat sheet

| If this goes wrong | Do this |
| --- | --- |
| Bad tar / test restore | Delete test volume only. Live volume stays |
| NAS still unhealthy | Stay on Windows. No copies |
| Drive ACL leak | Remove the user; do not “reset the volume” |
| Spare External Media mis-mounted | Stop spare container. Check the live compose still has **one** volume on `/data` |
| NAS-hosted PicPeak fails | Use Windows `:3000` + original volume. Do not `-v` |
| Anyone suggests `down -v` or `volume rm` | Refuse |

---

## Success for the first implementation (Stage 1)

- [ ] Tar exists on another disk
- [ ] `jwt.secret` present in the tar
- [ ] Spare PicPeak on `:3001` opened a real gallery
- [ ] Live `:3000` and `elp-picpeak-data` unchanged
- [ ] You wrote the date and file path of that tar somewhere you can find

Then stop and wait for the next approved stage.
