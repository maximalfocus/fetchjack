#!/usr/bin/env bash
# One-shot disposable demo: builds the image, starts the three applications and
# the fixtures on fresh temporary databases, runs the scripted comparison, and
# tears everything down. Docker Compose is the only host requirement.
#
# Pass extra CLI flags through, e.g. `scripts/demo.sh --verbose`.
set -euo pipefail

cleanup() {
  ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable run --rm --build demo "$@"
