#!/usr/bin/env bash
# Verify the two-action opt-in gate and the vulnerable SSRF outcomes against the
# live stack. Requires the image to be built. Leaves services running; the caller
# is responsible for `docker compose down -v`.
set -euo pipefail

post() {
  curl -s -X POST "http://127.0.0.1:$1/previews" \
    -H "Authorization: Bearer demo-token-ada" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"$2\"}"
}

wait_healthz() {
  for _ in $(seq 1 30); do
    if curl -sf -o /dev/null "http://127.0.0.1:$1/healthz"; then return 0; fi
    sleep 1
  done
  return 1
}

echo "1) default 'up' must not start the vulnerable application"
docker compose up -d >/dev/null
if [ -n "$(docker compose ps -q vulnerable 2>/dev/null)" ]; then
  echo "FAIL: vulnerable was started by the default compose path" >&2
  exit 1
fi
echo "   ok"

echo "2) profile enabled but no acknowledgement must be refused with an explanation"
docker compose --profile vulnerable up -d vulnerable >/dev/null 2>&1 || true
sleep 3
if ! docker compose logs vulnerable 2>&1 | grep -q "Refusing to start"; then
  echo "FAIL: vulnerable did not refuse to start without ALLOW_VULNERABLE_DEMO=true" >&2
  docker compose logs vulnerable >&2 || true
  exit 1
fi
docker compose --profile vulnerable rm -sf vulnerable >/dev/null 2>&1 || true
echo "   ok"

echo "3) profile + acknowledgement starts it on 127.0.0.1:8001 and demonstrates SSRF"
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable up -d vulnerable >/dev/null
if ! wait_healthz 8001; then
  echo "FAIL: vulnerable not reachable on 127.0.0.1:8001" >&2
  docker compose logs vulnerable >&2 || true
  exit 1
fi

file_body="$(post 8001 'file:///app/secrets/preview_worker.env')"
if ! printf '%s' "$file_body" | grep -q "PREVIEW_WORKER_TOKEN"; then
  echo "FAIL: file:// did not return the fictional secret contents: $file_body" >&2
  exit 1
fi
echo "   ok: file:// returned the fictional secret file's contents"

internal_body="$(post 8001 'http://backoffice.larkspur.internal/service-account')"
if ! printf '%s' "$internal_body" | grep -q "service_account_token"; then
  echo "FAIL: internal host did not return the fictional credential: $internal_body" >&2
  exit 1
fi
echo "   ok: internal-host reach returned the fictional credential"

echo "ALL OPT-IN CHECKS PASSED"
