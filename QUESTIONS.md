# Questions before any implementation

Please answer in this file or in the PR. Short answers are enough. Do not give passwords or public IPs.

## Synology

1. **Model** — e.g. DS920+, DS1522+ (the exact model).
2. **DSM version.**
3. **Storage pool status** right now — Healthy / Degraded / Crashed / Missing / unknown.
4. **RAID or SHR type**, how many drives, and any unused or failed bays.
5. **Total and free space** on the volume we would use (TB, not “looks fine”).
6. Has DSM ever asked you to **initialise, repair, or create a new pool**? If yes, what did you click?
7. Is **Hyper Backup** (or another NAS backup) already running? To where (USB, second NAS, C2, nothing)?
8. Is **Synology Drive** already installed?

## Network

9. Typical **upload and download** (home/studio). Rough Mbps is fine.
10. How do you reach the NAS today — LAN only, QuickConnect, Tailscale/VPN, port-forward, or not sure?
11. Do you already own a **domain** you want for galleries, or should links stay on LAN/Tailscale for now?

## Work

12. Will **Windows Docker Desktop** keep hosting PicPeak for the next stretch? (Recommended: yes.)
13. How many **photo editors** and **video editors**, and do they work on-site, remote, or both?
14. Typical event size — photo count and video minutes/hours.
15. Where do editors work today (Lightroom, Premiere, DaVinci, other)?
16. Any **existing NAS folder names** we must keep?

## Gallery

17. About how many **live client galleries** are in PicPeak now (the ~126 photos plus any newer)?
18. Are you happy to **stop using Studio Console `:3080`** and use http://localhost:3000/admin only?
19. Have you ever run the **volume tar** in `docs/storage.md`, and did you try a restore?

You do not need to answer everything at once. **1–5, 12, 18** are enough to start Stage 1 (backup drill) after you approve the plan.
