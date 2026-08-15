# Security policy

This project is a deliberately vulnerable teaching exercise. That makes "is this a security bug?"
an unusually confusing question here, so this document answers it directly.

## The flaw in this repository is the product

Two of the three applications ship a real, working Server-Side Request Forgery on purpose:

- the **vulnerable** application fetches whatever URL is submitted with no validation at all, so it
  resolves `file://` and reaches internal-only hosts; and
- the **naive** application validates only the URL that was *submitted*, then follows redirects
  without re-checking each hop, so an allowlisted host that redirects inward defeats it.

**Please do not report these.** They are the subject being taught, they are documented in
[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md), and the tests assert that they still work. The same goes
for the demo bearer tokens, which are constants in this repository and protect nothing, and for the
fictional fixtures — the internal "service account" credential and the local `preview_worker.env`
file, both of which say in their own contents that they are invented.

The **secure** application is different. It is the demonstration of the fix, and it is meant to hold.

## What is worth reporting

Anything that is *not* the lesson. For example:

- a way to make the **secure** application fetch a target whose scheme or host is not allowlisted,
  disclose a fixture, create a record from a rejected submission, or reveal which check refused a
  submission;
- a way past the allowlist on a redirect hop, or a hop that is contacted before it is validated;
- anything that escapes the demo container or affects the machine running it;
- anything that reaches the public internet — no component here should make any outbound connection
  beyond the demo's own container network;
- a way to start one of the intentionally vulnerable applications without both deliberate opt-in
  actions; or
- a real credential, personal datum, or non-fictional detail that has ended up in this repository or
  its history.

## How to report

Use **[private vulnerability reporting](https://github.com/maximalfocus/fetchjack/security/advisories/new)**
on this repository. That opens a report only the maintainer can see.

Please do not open a public issue for anything in the list above. For ordinary bugs, feature ideas,
and questions about the teaching material, a public issue is exactly right.

A useful report says what you did, what happened, and what you expected instead. Please keep any
proof of concept inside the project's own container and against its own fixtures.

## Scope and expectations

This is educational material published as-is under the [MIT License](LICENSE). It is not a service
and nothing here is hosted. There is no support commitment, no response-time undertaking, no release
schedule, and no compatibility guarantee — the licence's warranty disclaimer is the whole of it.
Reports are read and handled on a best-effort basis, and you are welcome to fix something yourself;
see [CONTRIBUTING.md](CONTRIBUTING.md).
