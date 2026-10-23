# Apply Phase 2 to the existing Windows install

Your photos already live in Docker volume **`elp-picpeak-data`**. These steps do not rebuild PicPeak and must not delete that volume.

**Never run:** `docker compose down -v`

## 1. Update the project files (Cursor)

Pull or check out this branch in Cursor Desktop so `apps/gallery` contains the new scripts and Studio Console. Do not create a new repository.

## 2. Confirm Docker is running

Whale icon → Engine running. Your current galleries should still open at http://localhost:3000

## 3. Enable video + optional email (does not delete galleries)

In PowerShell:

```powershell
cd <repo>\apps\gallery
copy .env.example .env   # skip if .env already exists
python scripts\apply-platform-settings.py --dry-run
python scripts\apply-platform-settings.py
```

Use the **same** `ADMIN_PASSWORD` already in your working `.env`. The script only changes PicPeak **settings**, CSS templates, and missing event types.

If you prefer the mouse: PicPeak Admin → Settings → General → Allowed File Types → add `mp4,mov,webm` (keep jpg/jpeg/png/webp). Event Defaults → turn off **Require customer email**.

After this, the native **Upload Photos & Videos** picker should accept MP4. That is PicPeak’s real video support — not a fake `accept=` hack.

## 4. Start the Studio Console (optional, recommended)

```powershell
cd <repo>\apps\gallery
docker compose up -d studio-console
```

Open http://localhost:3080  
Log in with the same admin user as PicPeak.

PicPeak Admin remains at http://localhost:3000/admin.

## 5. Test one feature at a time

1. Existing gallery still opens and shows the ~126 photos  
2. Create an event **without** an email  
3. Switch wizard tabs; data should remain  
4. Copy gallery link  
5. Share via WhatsApp (opens WhatsApp / WhatsApp Web with the brand name)  
6. Mini Momentz / Katha Films / Tattva Weddings each selectable  
7. Upload a small H.264 MP4; confirm thumbnail + player  
8. Phone and desktop browser  
9. Volume still named `elp-picpeak-data` (`docker volume ls`)  
10. `.env` is not committed
11. Studio Console → **Storage**: usage, 70/85/95% alerts, per-event photo/video, remaining-capacity estimate. Confirm it does **not** delete anything. Optional: `python scripts\storage-report.py`

## 6. If compose warns it will recreate `picpeak`

Stop. Check `docker volume ls` includes `elp-picpeak-data`. Recreating the **container** is OK; removing the **volume** is not. Cancel anything that says it will delete `elp-picpeak-data`.
