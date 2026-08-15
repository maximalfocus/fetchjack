# fetchjack

**fetchjack** is a small, container-only **educational** demonstration of
**Server-Side Request Forgery (SSRF)** — OWASP A10:2021 / API7:2023 / CWE-918.
It shows how a link-preview feature that fetches a URL on the server's behalf can
be turned into a way to reach places the user never could directly, and how a
**scheme and host allowlist enforced on every request the server makes** prevents
it.

> ⚠️ **This repository is intentionally vulnerable on purpose.** Two of its three
> applications ship a real SSRF flaw so you can watch it work and then watch the
> fix stop it. It is local educational code and **must never be deployed**. It
> ships no working exploit against anything but itself, contacts no real system,
> and performs no access to the public internet. Every host, user, token,
> credential, and fixture file is wholly fictional.

Everything runs locally under **Docker Compose**. There is **no hosted service**,
nothing is published as an image or a package, and nothing here makes any
production-readiness claim.

## Safety boundary

- Fully simulated and self-contained: all fetch targets are in-network fixtures
  the environment itself provides.
- Hermetic: no component reaches the public internet; every outbound request
  stays inside the container network.
- Fictional data only: every fixture standing in for a secret declares in its own
  contents that it is fictional.
- Gated: neither intentionally vulnerable application starts without **two**
  deliberate opt-in actions.

## License and policies

Released under the [MIT License](LICENSE). Before reporting a security issue,
please read [SECURITY.md](SECURITY.md) — it explains which flaws are the lesson
and must not be reported, and gives a private path for the ones that are genuine.
Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Walkthrough

New to SSRF? Read **[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md)** — a ~5-minute,
source-free tour of why a server-side fetch crosses a trust boundary, the four
demonstration cases and their expected outcomes, why an allowlist beats a
denylist, why validating only the submitted URL is not enough, and what is
deliberately out of scope.

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

Each application also exposes its generated OpenAPI documentation locally, e.g.
for the secure app: `http://127.0.0.1:8000/docs` (Swagger UI) and
`http://127.0.0.1:8000/openapi.json` (raw schema).

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

## One-shot comparison demo

The simplest way to see all three applications side by side is the disposable
demo, which starts the apps and fixtures on fresh databases, runs the scripted
comparison, prints a per-application verdict, and tears everything down:

```sh
scripts/demo.sh            # scripted comparison
scripts/demo.sh --verbose  # also show hops, allowlist decisions, and bodies
```

It submits the same four cases (`file://` scheme abuse, internal-host reach,
allowlisted-host redirect bypass, and a legitimate preview) to each application
and reports whether each returned the fictional secret/credential and what it
stored — yielding `SECURE`, `VULNERABLE`, and `NAIVE` verdicts. Docker Compose is
the only host requirement, and the run completes in well under five minutes.

An interactive mode is also available (submit your own URLs to all three apps):

```sh
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable run --rm demo \
  python -m fetchjack.cli --interactive
```

## In-network fixtures

The demonstration provides, reachable **only inside the container network**:

- **`assets.larkspur.test`** — the allowlisted upstream fixture: deterministic
  preview content at `/notes/{n}` and a redirect endpoint `/r?to={url}`.
- **`backoffice.larkspur.internal`** — an internal-only fixture (never
  allowlisted, never published to the host) serving a fictional internal service
  credential at `/service-account`.
- **`/app/secrets/preview_worker.env`** — a local fixture file baked into the
  image, standing in for a local secret; its own contents declare it fictional.

## Deliberately out of scope

To keep one lesson clear, this demo does **not** address — and its host allowlist
is **not** a defence against — resolved-address and link-local blocking
(`127.0.0.0/8`, `169.254.0.0/16`, `::1`, RFC 1918) as the taught control, cloud
metadata retrieval, or DNS rebinding and TOCTOU on hostname resolution. These are
out of scope **by design**, not oversights;
[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) §7 says so explicitly.
