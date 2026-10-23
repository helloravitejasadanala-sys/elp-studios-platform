# PicPeak smoke test results

- When (UTC): 2026-10-23T09:54:45Z
- Origin: `http://127.0.0.1:3000`
- Image: `picpeak/aio:stable`
- Pass: **15** / Fail: **0** / Skip: **0**

| Status | Check | Detail |
| --- | --- | --- |
| PASS | Health endpoint | HTTP 200 {"status":"ok"} |
| PASS | Admin login | user=admin |
| PASS | Admin password change not required | mustChangePassword=false |
| PASS | Reject bad admin password | HTTP 401 |
| PASS | Create gallery | id=2 slug=other-smoke-test-gallery-20261023-095444-2026-10-01 |
| PASS | Upload demo photographs | count=4 |
| PASS | Publish gallery | {"message":"Event published successfully","is_draft":false,"notified_customer":false} |
| PASS | Client gallery link / info | requires_password=True share=/gallery/other-smoke-test-gallery-20261023-095444-2026-10-01/f120a8658d971b8bbdfb66c1f4895bcc |
| PASS | Reject wrong gallery password | HTTP 401 |
| PASS | Password-protected guest login | token issued |
| PASS | Photos require auth | HTTP 401 |
| PASS | Guest can list photos | count=2 |
| PASS | Photo favourites | {"success":true,"id":2,"created":true} |
| PASS | Single photo download | HTTP 200 bytes=49855 |
| PASS | Download all (ZIP) | HTTP 200 bytes=42601 |

## Notes

- Demo credentials live only in local `.env` (gitignored).
- Guest share path shape: `/gallery/<slug>/<share_token>`.
- Mobile-responsive UI verified via Playwright screenshots (see Project store `media/gallery-prototype/`).
- Brand styling / video / expiry / branded hostnames: see root `IMPLEMENTED.md`.
