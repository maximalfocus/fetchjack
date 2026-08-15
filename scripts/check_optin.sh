#!/usr/bin/env bash
# Verify the two-action opt-in gate and the non-secure applications' outcomes
# against the live stack. Requires the image to be built. Leaves services
# running; the caller is responsible for `docker compose down -v`.
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

echo "1) default 'up' must not start the non-secure applications"
docker compose up -d >/dev/null
for svc in vulnerable naive; do
  if [ -n "$(docker compose ps -q "$svc" 2>/dev/null)" ]; then
    echo "FAIL: $svc was started by the default compose path" >&2
    exit 1
  fi
done
echo "   ok"

echo "2) profile enabled but no acknowledgement must be refused with an explanation"
docker compose --profile vulnerable up -d vulnerable naive >/dev/null 2>&1 || true
for svc in vulnerable naive; do
  found=""
  for _ in $(seq 1 30); do
    if docker compose logs "$svc" 2>&1 | grep -q "Refusing to start"; then found=1; break; fi
    sleep 1
  done
  if [ -z "$found" ]; then
    echo "FAIL: $svc did not refuse to start without ALLOW_VULNERABLE_DEMO=true" >&2
    docker compose logs "$svc" >&2 || true
    exit 1
  fi
done
docker compose --profile vulnerable rm -sf vulnerable naive >/dev/null 2>&1 || true
echo "   ok"

echo "3) profile + acknowledgement starts them and demonstrates the outcomes"
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable up -d >/dev/null
wait_healthz 8000 || { echo "FAIL: secure not reachable on 8000" >&2; exit 1; }
wait_healthz 8001 || { echo "FAIL: vulnerable not reachable on 8001" >&2; exit 1; }
wait_healthz 8002 || { echo "FAIL: naive not reachable on 8002" >&2; exit 1; }

# Vulnerable: file:// scheme abuse and internal reach.
if ! printf '%s' "$(post 8001 'file:///app/secrets/preview_worker.env')" | grep -q "PREVIEW_WORKER_TOKEN"; then
  echo "FAIL: vulnerable file:// did not return the fictional secret" >&2; exit 1
fi
echo "   ok: vulnerable file:// returned the fictional secret file's contents"
if ! printf '%s' "$(post 8001 'http://backoffice.larkspur.internal/service-account')" | grep -q "service_account_token"; then
  echo "FAIL: vulnerable internal-host did not return the fictional credential" >&2; exit 1
fi
echo "   ok: vulnerable internal-host returned the fictional credential"

# Naive: direct submissions rejected identically to the secure app.
for u in "file:///app/secrets/preview_worker.env" "http://backoffice.larkspur.internal/service-account"; do
  naive_resp="$(post 8002 "$u")"
  secure_resp="$(post 8000 "$u")"
  if [ "$naive_resp" != "$secure_resp" ]; then
    echo "FAIL: naive and secure responses differ for $u" >&2
    echo "  naive=$naive_resp" >&2; echo "  secure=$secure_resp" >&2
    exit 1
  fi
done
echo "   ok: naive rejects direct file:// and internal-host identically to secure"

# Naive: allowlisted-host redirect to internal target defeats it.
redir="$(post 8002 'http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account')"
if ! printf '%s' "$redir" | grep -q "service_account_token"; then
  echo "FAIL: naive redirect bypass did not return the fictional credential: $redir" >&2
  exit 1
fi
echo "   ok: naive is defeated by the allowlisted-host redirect to an internal target"

echo "ALL OPT-IN CHECKS PASSED"
