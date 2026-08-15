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

This builds the image, starts the in-network fixture targets, waits for them to
become healthy, and runs Ruff, mypy, and pytest against them. GitHub Actions runs
the identical command on every pull request.

To remove the fixture containers and network afterwards:

```sh
docker compose down -v
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

## Status

This is the foundational slice: the repository skeleton, the fictional Larkspur
workspace and preview-record model, the in-network fixture targets, the local
fixture secret file, and the containerized verification boundary with CI. The
secure, vulnerable, and naive preview applications, the comparison CLI, the
walkthrough, and the publication work arrive in later slices.
