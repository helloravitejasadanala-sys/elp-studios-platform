# PicPeak smoke test results

- When (UTC): 2026-10-23T10:55:24Z
- Origin: `http://127.0.0.1:3000`
- Image: `picpeak/aio:stable`
- Pass: **15** / Fail: **0** / Skip: **0**

| Status | Check | Detail |
| --- | --- | --- |
| PASS | Health endpoint | HTTP 200 {"status":"ok"} |
| PASS | Admin login | user=admin |
| PASS | Admin password change not required | mustChangePassword=false |
| PASS | Reject bad admin password | HTTP 401 |
| PASS | Create gallery | id=6 slug=other-smoke-test-gallery-20261023-105523-2026-10-01 |
| PASS | Upload demo photographs | count=4 |
| PASS | Publish gallery | {"message":"Event published successfully","is_draft":false,"notified_customer":false} |
| PASS | Client gallery link / info | requires_password=True share=/gallery/other-smoke-test-gallery-20261023-105523-2026-10-01/2da8b55fea7714c6b2920adb7ad84771 |
| PASS | Reject wrong gallery password | HTTP 401 |
| PASS | Password-protected guest login | token issued |
| PASS | Photos require auth | HTTP 401 |
| PASS | Guest can list photos | count=4 |
| PASS | Photo favourites | {"success":true,"id":3,"created":true} |
| PASS | Single photo download | HTTP 200 bytes=49855 |
| PASS | Download all (ZIP) | HTTP 200 bytes=41455 |

## Notes

- Demo credentials live only in local `.env` (gitignored).
- Guest share path shape: `/gallery/<slug>/<share_token>`.
- Mobile-responsive UI verified via Playwright screenshots (see Project store `media/gallery-prototype/`).
- Brand styling / video / expiry / branded hostnames: see root `IMPLEMENTED.md`.
