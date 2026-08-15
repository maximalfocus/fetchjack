# fetchjack

**fetchjack** is a small, container-only **educational** demonstration of
**Server-Side Request Forgery (SSRF)** — OWASP A10:2021 / API7:2023 / CWE-918.
It shows how a link-preview feature that fetches a URL on the server's behalf can
be turned into a way to reach places the user never could directly, and how a
**scheme and host allowlist enforced on every request the server makes** prevents
it.

> **This repository is under private development.** It is local educational code.
> It ships no working exploit, contacts no real system, and performs no access to
> the public internet. Every host, token, credential, and fixture file is wholly
> fictional. No license is granted yet.

## Safety boundary

- Fully simulated and self-contained: all fetch targets are in-network fixtures
  the environment itself provides.
- Hermetic: no component reaches the public internet; every outbound request
  stays inside the container network.
- Fictional data only: every fixture standing in for a secret declares in its own
  contents that it is fictional.

## Requirements

Only **Docker** (with Compose v2) is required on the host. Python, project
dependencies, `uv`, pytest, Ruff, and mypy all run **inside containers** — the
host needs no Python environment.

## Verification

Run the full test + Ruff + mypy gate through one command:

```sh
docker compose run --rm --build verify
```

This builds the image, starts the in-network fixture targets and the secure
service, waits for them to become healthy, and runs Ruff, mypy, and pytest
against them. GitHub Actions runs the identical command on every pull request.

To remove the containers and network afterwards:

```sh
docker compose down -v
```

## Running the secure application

The secure application is the default long-running service. Start it (with its
fixtures) and reach it on loopback:

```sh
docker compose up -d
curl http://127.0.0.1:8000/healthz
```

It authenticates fictional users with demo-only bearer tokens and exposes:

- `POST /previews` — submit a URL; the server fetches it and stores a preview
  record. A legitimate allowlisted URL returns `201`; any target whose scheme or
  host is not allowlisted — including a redirect to a non-allowlisted host — is
  rejected with a generic `400` and a structured rejection event on stdout.
- `GET /previews` — the authenticated user's preview history.

```sh
# A legitimate preview (201):
curl -X POST http://127.0.0.1:8000/previews \
  -H "Authorization: Bearer demo-token-ada" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://assets.larkspur.test/notes/1"}'
```

The secure application enforces a **scheme allowlist** (`http`, `https`) and a
**host allowlist** (only `assets.larkspur.test`) on **every** request it makes,
re-validating each redirect hop before contacting it.

## The vulnerable application (opt-in)

> ⚠️ The vulnerable application has **no** SSRF protection and is local
> educational code only. **Never deploy it.**

It is not started by the default `docker compose up`. Starting it requires **two**
deliberate actions — enabling the `vulnerable` Compose profile **and** setting
`ALLOW_VULNERABLE_DEMO=true`. With either missing, it refuses to start and
explains why.

```sh
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable up -d vulnerable
```

It listens on `127.0.0.1:8001` and fetches whatever URL is submitted, with no
validation, following redirects and resolving `file://`:

```sh
# Scheme abuse — returns the fictional local secret file's contents:
curl -X POST http://127.0.0.1:8001/previews \
  -H "Authorization: Bearer demo-token-ada" -H "Content-Type: application/json" \
  -d '{"url":"file:///app/secrets/preview_worker.env"}'

# Internal reach — returns the fictional internal service credential:
curl -X POST http://127.0.0.1:8001/previews \
  -H "Authorization: Bearer demo-token-ada" -H "Content-Type: application/json" \
  -d '{"url":"http://backoffice.larkspur.internal/service-account"}'
```

## The naive application (opt-in)

> ⚠️ The naive application is intentionally half-fixed — local educational code
> only. **Never deploy it.**

Under the **same** two-action opt-in gate, the naive application listens on
`127.0.0.1:8002`. It validates only the *submitted* URL against the allowlist —
so it rejects a direct `file://` or internal-host submission exactly as the
secure app does — but then follows redirects **without re-validating** each hop:

```sh
# Rejected exactly like the secure app (generic 400):
curl -X POST http://127.0.0.1:8002/previews \
  -H "Authorization: Bearer demo-token-ada" -H "Content-Type: application/json" \
  -d '{"url":"http://backoffice.larkspur.internal/service-account"}'

# But defeated by an allowlisted host that redirects to an internal target (201):
curl -X POST http://127.0.0.1:8002/previews \
  -H "Authorization: Bearer demo-token-ada" -H "Content-Type: application/json" \
  -d '{"url":"http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"}'
```

This shows why validating only the submitted URL is **necessary but not
sufficient** once redirects are followed.

`scripts/check_optin.sh` verifies the opt-in gate and the vulnerable and naive
outcomes end to end.

## In-network fixtures

The demonstration provides, reachable **only inside the container network**:

- **`assets.larkspur.test`** — the allowlisted upstream fixture: deterministic
  preview content at `/notes/{n}` and a redirect endpoint `/r?to={url}`.
- **`backoffice.larkspur.internal`** — an internal-only fixture (never
  allowlisted, never published to the host) serving a fictional internal service
  credential at `/service-account`.
- **`/app/secrets/preview_worker.env`** — a local fixture file baked into the
  image, standing in for a local secret; its own contents declare it fictional.

## Status

Delivered so far: the repository skeleton, the fictional Larkspur workspace and
preview-record model, the in-network fixture targets, the local fixture secret
file, the containerized verification boundary with CI, the **secure preview
service** (the fixed reference implementation), and the **vulnerable** and
**naive** applications behind their two-action opt-in gate. The comparison CLI,
the walkthrough, and the publication work arrive in later slices.
