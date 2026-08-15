# fetchjack walkthrough — Server-Side Request Forgery (SSRF)

This walkthrough takes about five minutes and needs only Docker Compose. Every
user, host, token, credential, and file in it is **wholly fictional**; nothing
here contacts a real system or the public internet.

- **Vulnerability:** Server-Side Request Forgery — OWASP **A10:2021**, API Security
  **API7:2023**, **CWE-918**.
- **The fix it teaches:** a **scheme and host allowlist enforced on every request
  the server makes, including each redirect hop.**

> ⚠️ The **vulnerable** and **naive** applications are intentionally flawed, local
> educational code. **Never deploy them.**

## 1. Why a server-side fetch crosses a trust boundary

When your browser fetches a URL, the request comes from *your* machine, on *your*
network. You can only reach what your own network position allows — you cannot
reach a company's internal-only services or read files on their servers.

A **link-preview** feature changes who makes the request. You submit a URL and the
**server** fetches it *on your behalf*, from *inside* its own trusted network. The
server can reach things you never could: internal-only hosts, cloud metadata
endpoints, and — depending on how it fetches — local files. If the server fetches
whatever URL you hand it, you have borrowed its network position. That is SSRF:
the server becomes a **confused deputy** at the network boundary, making requests
its own trust lets through but that should never have been allowed on your behalf.

The trust boundary being crossed is **the edge of the server's network**. The
control that matters is therefore on **every outbound request the server makes**,
not on the shape of the URL you typed.

## 2. The fictional scenario

**Larkspur** is an invented team-notes workspace whose link-preview feature
fetches a submitted URL server-side and returns a small preview. The environment
provides, reachable **only inside the container network**:

- **`assets.larkspur.test`** — the allowlisted upstream: benign content at
  `/notes/{n}` and a redirect endpoint `/r?to={url}`. This stands in for the one
  external content source the feature is meant to use, and is the **only** member
  of the secure host allowlist.
- **`backoffice.larkspur.internal`** — an internal-only fixture, never allowlisted
  and never published, serving a **fictional** internal service credential at
  `/service-account`.
- **`/app/secrets/preview_worker.env`** — a local file inside the image, standing
  in for a local secret; its own contents declare it fictional.

Three applications expose the identical API (`POST /previews`, `GET /previews`,
demo bearer auth) and differ **only** in how they validate the fetch target:

| App | Validation |
|---|---|
| **secure** (`:8000`, default) | Scheme + host allowlist on **every** hop, redirects re-validated before contact |
| **vulnerable** (`:8001`, opt-in) | **None** — fetches anything, follows redirects, resolves `file://` |
| **naive** (`:8002`, opt-in) | Validates only the **submitted** URL, then follows redirects **without** re-checking |

## 3. Run it

Start everything on fresh state, run the scripted comparison, and tear it down:

```sh
scripts/demo.sh            # per-application verdicts
scripts/demo.sh --verbose  # + redirect chain, per-hop allowlist decision, bodies
```

Explore an application's generated OpenAPI documentation locally (the secure app
is the default service):

```sh
docker compose up -d
open http://127.0.0.1:8000/docs        # Swagger UI   (or curl the raw schema:)
curl http://127.0.0.1:8000/openapi.json
```

Run the automated security regression matrix:

```sh
docker compose run --rm --build verify
```

## 4. The four cases and their expected outcomes

The demo submits the same four cases to each application. All tokens shown are
demo-only (`demo-token-ada`).

### Case 1 — `file://` scheme abuse
Submit `file:///app/secrets/preview_worker.env`.

- **vulnerable:** `201 Created` — the preview body **contains the fictional secret
  file's contents**. (It resolves the `file://` scheme with no validation.)
- **naive** and **secure:** identical generic `400 Bad Request`, no record — the
  scheme `file` is not allowlisted.

### Case 2 — internal-host reach
Submit `http://backoffice.larkspur.internal/service-account`.

- **vulnerable:** `201 Created` — the body **contains the fictional internal
  credential** that no external caller can reach directly.
- **naive** and **secure:** identical generic `400`, no record — the host is not
  allowlisted.

### Case 3 — allowlisted-host redirect bypass
Submit `http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account`.
The submitted host (`assets.larkspur.test`) **is** allowlisted; it replies `302`
to the internal host.

- **vulnerable:** `201` — follows the redirect and returns the internal credential.
- **naive:** `201` — the *submitted* URL passed, and it follows the redirect
  **without re-validating** the hop, so it too returns the internal credential.
- **secure:** generic `400`, no record — it **re-validates the redirect target
  before contacting it**, and `backoffice.larkspur.internal` is not allowlisted.

### Case 4 — legitimate preview
Submit `http://assets.larkspur.test/notes/1`.

- **all three:** `201` with the same deterministic preview and exactly one new
  record. The fix changes only the security-relevant behaviour — **secure and
  vulnerable return byte-identical bodies** for this benign input.

**Verdicts:** `secure` → SECURE (every attack rejected), `vulnerable` → VULNERABLE
(every attack succeeds), `naive` → NAIVE (direct attacks rejected, redirect bypass
succeeds).

## 5. Why the allowlist is the control — and a denylist is not

A tempting "fix" is to **denylist** addresses that look internal (for example
`127.0.0.0/8`, `169.254.0.0/16`, RFC 1918 ranges, `::1`). This is the **weaker**
control: a denylist enumerates what you already know is dangerous, and it is
routinely bypassed by alternate encodings, less-obvious internal names, redirects,
and DNS tricks. Anything you forgot to list is allowed.

A **validated allowlist** of permitted **schemes and hosts** is the **stronger**
control: it enumerates the (usually tiny) set of things that are *allowed*, and
denies everything else by default. Here the allowlist admits only `http`/`https`
and only `assets.larkspur.test`. This demo deliberately does **not** present a
denylist of "internal" ranges as the fix.

## 6. Why validating only the submitted URL is not enough

The naive application shows the trap: it validates the URL you submitted, which
correctly rejects a direct `file://` or internal-host submission — but it then
follows redirects **without re-checking each hop**. An allowlisted host that
redirects inward defeats it (Case 3). The allowlist must be enforced on **every
request the server makes**, re-validating (or refusing) each redirect `Location`
before contacting it, under a fixed hop cap. Validating only the submitted URL is
**necessary but not sufficient**.

## 7. Deliberately out of scope

To keep one lesson clear, this demo does **not** address — and its hostname
allowlist is **not** a defence against — the following, each of which is its own
separate demonstration:

- **Resolved-address / link-local blocking** (`127.0.0.0/8`, `169.254.0.0/16`,
  `::1`, RFC 1918) as the taught control;
- **cloud-metadata retrieval** (e.g. `169.254.169.254`); and
- **DNS rebinding / TOCTOU** on hostname resolution.

These are out of scope **by design**, not oversights.
