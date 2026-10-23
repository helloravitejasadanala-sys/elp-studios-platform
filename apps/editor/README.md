# Editor workspace (Priority 2)

Simple web UI for photo editors (e.g. Rajesh) and studio admins.

## Scope for the demo

- Login + roles (`admin`, `editor`)
- Assigned bookings/projects only (local demo data)
- Deadlines / status / waiting-for-whom
- References + instructions
- Source download links (stub URLs — no NAS)
- Edited submission + review comments / revisions
- Final approval

## Storage

Local JSON / file adapters under `apps/editor/.data/` (gitignored).  
Interfaces for Synology Drive / Tailscale are stubs only — **never connect to NAS from agents**.

## Status

Scaffolded. Run gallery Priority 1 first (`apps/gallery`). Editor UI lands next once the gallery remote exists.
