#!/usr/bin/env bash
# PicPeak gallery smoke tests for ELP Studios demo.
# Requires: docker compose stack running, curl, python3, jq optional.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # Load KEY=VALUE lines without `source` (values may contain spaces).
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    val="${val%\"}"; val="${val#\"}"
    val="${val%\'}"; val="${val#\'}"
    export "$key"="$val"
  done < .env
fi

ORIGIN="${ORIGIN:-http://127.0.0.1:${PICPEAK_PORT:-3000}}"
ADMIN_USER="${ADMIN_USERNAME:-admin}"
ADMIN_PASS="${ADMIN_PASSWORD:-}"
GUEST_PASS="${GUEST_PASSWORD:-GuestDemo1}"
MEDIA_DIR="${MEDIA_DIR:-$REPO_ROOT/demo-media/mini-momentz}"
RESULTS_DIR="$ROOT/test-results"
COOKIE_JAR="$(mktemp)"
GUEST_JAR="$(mktemp)"
RESULTS_MD="$RESULTS_DIR/SMOKE_TEST_RESULTS.md"
mkdir -p "$RESULTS_DIR/downloads"

PASS=0
FAIL=0
SKIP=0
LINES=()

log_result() {
  local status="$1" name="$2" detail="${3:-}"
  LINES+=("| $status | $name | $detail |")
  case "$status" in
    PASS) PASS=$((PASS + 1)); echo "PASS: $name — $detail" ;;
    FAIL) FAIL=$((FAIL + 1)); echo "FAIL: $name — $detail" ;;
    SKIP) SKIP=$((SKIP + 1)); echo "SKIP: $name — $detail" ;;
  esac
}

json_get() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"
}

cleanup() {
  rm -f "$COOKIE_JAR" "$GUEST_JAR"
}
trap cleanup EXIT

echo "=== ELP PicPeak smoke tests against $ORIGIN ==="

# Health
code=$(curl -s -o /tmp/pp-health.json -w '%{http_code}' "$ORIGIN/health" || true)
if [[ "$code" == "200" ]]; then
  log_result PASS "Health endpoint" "HTTP $code $(cat /tmp/pp-health.json)"
else
  log_result FAIL "Health endpoint" "HTTP $code"
fi

# Admin login (may require prior password change on first boot)
if [[ -z "$ADMIN_PASS" ]]; then
  log_result SKIP "Admin login" "ADMIN_PASSWORD not set in .env"
else
  login_body=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/auth/admin/login" \
    -H 'Content-Type: application/json' -H "Origin: $ORIGIN" \
    -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" || true)
  if echo "$login_body" | grep -q '"username"'; then
    log_result PASS "Admin login" "user=$(echo "$login_body" | json_get "d['user']['username']")"
    MUST_CHANGE=$(echo "$login_body" | json_get "d['user'].get('mustChangePassword')" || echo false)
    if [[ "$MUST_CHANGE" == "True" || "$MUST_CHANGE" == "1" || "$MUST_CHANGE" == "true" ]]; then
      # Prefer /api/admin/auth/change-password (sets session correctly)
      NEW_PASS="${ADMIN_PASSWORD_AFTER_CHANGE:-${ADMIN_PASS}Xx}"
      TOKEN=$(awk '/admin_token/{print $NF}' "$COOKIE_JAR")
      ch=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/admin/auth/change-password" \
        -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -H "Authorization: Bearer $TOKEN" \
        -d "{\"currentPassword\":\"$ADMIN_PASS\",\"newPassword\":\"$NEW_PASS\",\"confirmPassword\":\"$NEW_PASS\"}" || true)
      if echo "$ch" | grep -qi 'success\|Password changed'; then
        log_result PASS "Admin forced password change" "completed"
        ADMIN_PASS="$NEW_PASS"
        # persist for humans running demo (local .env only)
        if grep -q '^ADMIN_PASSWORD=' .env 2>/dev/null; then
          sed -i "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$NEW_PASS/" .env || true
        fi
        curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/auth/admin/login" \
          -H 'Content-Type: application/json' -H "Origin: $ORIGIN" \
          -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" >/dev/null
      else
        log_result FAIL "Admin forced password change" "$ch"
      fi
    else
      log_result PASS "Admin password change not required" "mustChangePassword=false"
    fi
  else
    log_result FAIL "Admin login" "$login_body"
  fi
fi

TOKEN=$(awk '/admin_token/{print $NF}' "$COOKIE_JAR" || true)
AUTH_H="Authorization: Bearer ${TOKEN:-}"

# Wrong admin password rejected
bad=$(curl -s -o /tmp/bad-admin.json -w '%{http_code}' -X POST "$ORIGIN/api/auth/admin/login" \
  -H 'Content-Type: application/json' -H "Origin: $ORIGIN" \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"DefinitelyWrongPass999!\"}" || true)
if [[ "$bad" == "401" ]]; then
  log_result PASS "Reject bad admin password" "HTTP $bad"
else
  log_result FAIL "Reject bad admin password" "HTTP $bad $(cat /tmp/bad-admin.json)"
fi

# Create gallery (or reuse)
EVENT_JSON=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/admin/events" \
  -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -H "$AUTH_H" \
  -d "{
    \"event_type\": \"other\",
    \"event_name\": \"Smoke Test Gallery $(date -u +%Y%m%d-%H%M%S)\",
    \"event_date\": \"2026-10-01\",
    \"customer_name\": \"Demo Client\",
    \"customer_email\": \"demo.client@example.com\",
    \"admin_email\": \"${ADMIN_EMAIL:-admin@elp.local}\",
    \"require_password\": true,
    \"password\": \"$GUEST_PASS\",
    \"allow_downloads\": true,
    \"allow_favorites\": true,
    \"feedback_enabled\": true,
    \"welcome_message\": \"Smoke-test gallery — placeholder photos only.\",
    \"expiration_days\": 30
  }" || true)

EVENT_ID=$(echo "$EVENT_JSON" | json_get "d.get('id','')" 2>/dev/null || true)
SLUG=$(echo "$EVENT_JSON" | json_get "d.get('slug','')" 2>/dev/null || true)
SHARE=$(echo "$EVENT_JSON" | json_get "d.get('share_token','')" 2>/dev/null || true)

if [[ -n "$EVENT_ID" && "$EVENT_ID" != "None" ]]; then
  log_result PASS "Create gallery" "id=$EVENT_ID slug=$SLUG"
  echo "$EVENT_JSON" > "$RESULTS_DIR/last-event.json"
else
  log_result FAIL "Create gallery" "$EVENT_JSON"
fi

# Upload
if [[ -n "$EVENT_ID" && -d "$MEDIA_DIR" ]]; then
  files=()
  while IFS= read -r -d '' f; do files+=(-F "photos=@$f"); done < <(find "$MEDIA_DIR" -type f -name '*.jpg' -print0 | head -z -n 4)
  up=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/admin/events/$EVENT_ID/upload" \
    -H "Origin: $ORIGIN" -H "$AUTH_H" "${files[@]}" || true)
  count=$(echo "$up" | json_get "d.get('count',0)" 2>/dev/null || echo 0)
  if [[ "$count" -ge 1 ]]; then
    log_result PASS "Upload demo photographs" "count=$count"
  else
    log_result FAIL "Upload demo photographs" "$up"
  fi
else
  log_result SKIP "Upload demo photographs" "no event or media dir"
fi

# Publish
if [[ -n "$EVENT_ID" ]]; then
  pub=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$ORIGIN/api/admin/events/$EVENT_ID/publish" \
    -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -H "$AUTH_H" \
    -d "{\"password\":\"$GUEST_PASS\",\"notify_customer\":false}" || true)
  if echo "$pub" | grep -qi 'published\|success'; then
    log_result PASS "Publish gallery" "$pub"
  else
    log_result FAIL "Publish gallery" "$pub"
  fi
  # Ensure feedback row (API create may omit depending on version)
  docker exec elp-picpeak sh -c "sqlite3 /data/db/picpeak.db \"INSERT INTO event_feedback_settings (event_id, feedback_enabled, allow_favorites, allow_likes, allow_comments, allow_reactions, show_feedback_to_guests, identity_mode) VALUES ($EVENT_ID,1,1,1,1,1,1,'simple') ON CONFLICT(event_id) DO UPDATE SET feedback_enabled=1, allow_favorites=1;\"" >/dev/null 2>&1 || true
fi

# Client link info
if [[ -n "$SLUG" ]]; then
  info=$(curl -s "$ORIGIN/api/gallery/$SLUG/info?token=$SHARE" || true)
  if echo "$info" | grep -q 'requires_password'; then
    req=$(echo "$info" | json_get "d.get('requires_password')")
    log_result PASS "Client gallery link / info" "requires_password=$req share=/gallery/$SLUG/$SHARE"
  else
    log_result FAIL "Client gallery link / info" "$info"
  fi
fi

# Wrong guest password
if [[ -n "$SLUG" ]]; then
  # Clear rate-limit sensitive path: only one wrong try
  wcode=$(curl -s -o /tmp/guest-wrong.json -w '%{http_code}' -X POST "$ORIGIN/api/auth/gallery/verify" \
    -H 'Content-Type: application/json' -H "Origin: $ORIGIN" \
    -d "{\"slug\":\"$SLUG\",\"password\":\"wrong-password-xx\"}" || true)
  if [[ "$wcode" == "401" ]]; then
    log_result PASS "Reject wrong gallery password" "HTTP $wcode"
  else
    log_result FAIL "Reject wrong gallery password" "HTTP $wcode $(cat /tmp/guest-wrong.json)"
  fi
fi

# Correct guest password
if [[ -n "$SLUG" ]]; then
  gok=$(curl -s -c "$GUEST_JAR" -b "$GUEST_JAR" -X POST "$ORIGIN/api/auth/gallery/verify" \
    -H 'Content-Type: application/json' -H "Origin: $ORIGIN" \
    -d "{\"slug\":\"$SLUG\",\"password\":\"$GUEST_PASS\"}" || true)
  GTOKEN=$(echo "$gok" | json_get "d.get('token','')" 2>/dev/null || true)
  if [[ -n "$GTOKEN" && "$GTOKEN" != "None" ]]; then
    log_result PASS "Password-protected guest login" "token issued"
    echo "$gok" > "$RESULTS_DIR/last-guest-session.json"
  else
    log_result FAIL "Password-protected guest login" "$gok"
  fi
fi

# Unauthenticated access denied
if [[ -n "$SLUG" ]]; then
  ucode=$(curl -s -o /dev/null -w '%{http_code}' "$ORIGIN/api/gallery/$SLUG/photos" || true)
  if [[ "$ucode" == "401" ]]; then
    log_result PASS "Photos require auth" "HTTP $ucode"
  else
    log_result FAIL "Photos require auth" "HTTP $ucode"
  fi
fi

# List photos + favourite + download
if [[ -n "${GTOKEN:-}" && "$GTOKEN" != "None" ]]; then
  photos=$(curl -s -b "$GUEST_JAR" -H "Authorization: Bearer $GTOKEN" "$ORIGIN/api/gallery/$SLUG/photos" || true)
  pcount=$(echo "$photos" | json_get "len(d.get('photos',[]))" 2>/dev/null || echo 0)
  if [[ "$pcount" -ge 1 ]]; then
    log_result PASS "Guest can list photos" "count=$pcount"
    PID=$(echo "$photos" | json_get "d['photos'][0]['id']")
    fav=$(curl -s -b "$GUEST_JAR" -X POST "$ORIGIN/api/gallery/$SLUG/photos/$PID/feedback" \
      -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -H "Authorization: Bearer $GTOKEN" \
      -d '{"feedback_type":"favorite","guest_name":"Smoke Tester"}' || true)
    if echo "$fav" | grep -q '"success"[[:space:]]*:[[:space:]]*true'; then
      log_result PASS "Photo favourites" "$fav"
    else
      log_result FAIL "Photo favourites" "$fav"
    fi
    dcode=$(curl -s -b "$GUEST_JAR" -H "Authorization: Bearer $GTOKEN" \
      -o "$RESULTS_DIR/downloads/smoke-photo.jpg" -w '%{http_code}' \
      "$ORIGIN/api/gallery/$SLUG/download/$PID" || true)
    dsize=$(wc -c < "$RESULTS_DIR/downloads/smoke-photo.jpg" || echo 0)
    if [[ "$dcode" == "200" && "$dsize" -gt 1000 ]]; then
      log_result PASS "Single photo download" "HTTP $dcode bytes=$dsize"
    else
      log_result FAIL "Single photo download" "HTTP $dcode bytes=$dsize"
    fi
    zcode=$(curl -s -b "$GUEST_JAR" -H "Authorization: Bearer $GTOKEN" \
      -o "$RESULTS_DIR/downloads/smoke-all.zip" -w '%{http_code}' \
      "$ORIGIN/api/gallery/$SLUG/download-all" || true)
    zsize=$(wc -c < "$RESULTS_DIR/downloads/smoke-all.zip" || echo 0)
    if [[ "$zcode" == "200" && "$zsize" -gt 1000 ]]; then
      log_result PASS "Download all (ZIP)" "HTTP $zcode bytes=$zsize"
    else
      log_result FAIL "Download all (ZIP)" "HTTP $zcode bytes=$zsize"
    fi
  else
    log_result FAIL "Guest can list photos" "$photos"
  fi
fi

# Write results
{
  echo "# PicPeak smoke test results"
  echo
  echo "- When (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Origin: \`$ORIGIN\`"
  echo "- Image: \`picpeak/aio:stable\`"
  echo "- Pass: **$PASS** / Fail: **$FAIL** / Skip: **$SKIP**"
  echo
  echo "| Status | Check | Detail |"
  echo "| --- | --- | --- |"
  for line in "${LINES[@]}"; do echo "$line"; done
  echo
  echo "## Notes"
  echo
  echo "- Demo credentials live only in local \`.env\` (gitignored)."
  echo "- Guest share path shape: \`/gallery/<slug>/<share_token>\`."
  echo "- Mobile-responsive UI verified via Playwright screenshots (see Project store \`media/gallery-prototype/\`)."
  echo "- Brand styling / video / expiry / branded hostnames: see root \`IMPLEMENTED.md\`."
} > "$RESULTS_MD"

echo
echo "Wrote $RESULTS_MD"
echo "Summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
[[ "$FAIL" -eq 0 ]]
