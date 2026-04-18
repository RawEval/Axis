#!/usr/bin/env bash
# Axis — end-to-end smoke test.
# Runs: register → login → /me → /connectors → /feed → /agent/history
# Also tests: unauth rejection, wrong password rejection, duplicate register.
set -euo pipefail

GW=${GW:-http://localhost:8000}
WEB=${WEB:-http://localhost:3001}
EMAIL="smoke+$(date +%s)@raweval.com"
PASS="SmokeTestPassword!2026"

say() { printf "\n\033[1;34m▶ %s\033[0m\n" "$*"; }
ok()  { printf "  \033[0;32m✓\033[0m %s\n" "$*"; }
fail(){ printf "  \033[0;31m✗\033[0m %s\n" "$*"; exit 1; }

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
json() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get(sys.argv[1],''))" "$1"; }

say "Health"
[ "$(code "$GW/healthz")" = "200" ]       && ok "api-gateway" || fail "api-gateway down"
[ "$(code "$GW/../8006/healthz" || echo)" != "" ] || true
[ "$(code http://localhost:8006/healthz)" = "200" ] && ok "auth-service" || fail "auth-service down"

say "Register new user"
RESP=$(curl -sS -X POST "$GW/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"name\":\"Smoke Test\"}")
TOKEN=$(echo "$RESP" | json access_token)
USER_ID=$(echo "$RESP" | json user_id)
[ -n "$TOKEN" ] && ok "register ok, user_id=$USER_ID" || fail "no token returned: $RESP"

say "Duplicate register"
STATUS=$(code -X POST "$GW/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
[ "$STATUS" = "409" ] && ok "409 on duplicate" || fail "expected 409, got $STATUS"

say "Login"
LOGIN=$(curl -sS -X POST "$GW/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$LOGIN" | json access_token)
[ -n "$TOKEN" ] && ok "login returned token" || fail "login failed: $LOGIN"

say "Wrong password"
STATUS=$(code -X POST "$GW/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"WrongPassword12345!\"}")
[ "$STATUS" = "401" ] && ok "401 on wrong password" || fail "expected 401, got $STATUS"

say "/auth/me with token"
ME=$(curl -sS "$GW/auth/me" -H "Authorization: Bearer $TOKEN")
ME_EMAIL=$(echo "$ME" | json email)
[ "$ME_EMAIL" = "$EMAIL" ] && ok "me returns correct email" || fail "me wrong: $ME"

say "/auth/me without token"
STATUS=$(code "$GW/auth/me")
[ "$STATUS" = "401" ] && ok "401 without token" || fail "expected 401, got $STATUS"

say "/connectors (protected)"
CONN=$(curl -sS "$GW/connectors" -H "Authorization: Bearer $TOKEN")
COUNT=$(echo "$CONN" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
[ "$COUNT" = "5" ] && ok "5 connector tiles returned" || fail "expected 5 tiles, got $COUNT"

say "/feed"
FEED_CODE=$(code "$GW/feed" -H "Authorization: Bearer $TOKEN")
[ "$FEED_CODE" = "200" ] && ok "feed 200" || fail "feed $FEED_CODE"

say "/agent/history"
HIST_CODE=$(code "$GW/agent/history" -H "Authorization: Bearer $TOKEN")
[ "$HIST_CODE" = "200" ] && ok "history 200" || fail "history $HIST_CODE"

say "Web middleware redirects unauth"
CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$WEB/feed")
[ "$CODE" = "307" ] && ok "web /feed → 307" || fail "web $CODE"

say "Web login page"
CODE=$(code "$WEB/login")
[ "$CODE" = "200" ] && ok "web /login → 200" || fail "web login $CODE"

printf "\n\033[1;32m✓ all smoke tests passed\033[0m\n"
printf "  user: %s\n  user_id: %s\n" "$EMAIL" "$USER_ID"
