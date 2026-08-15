"""Scripted comparison CLI for the three preview applications.

The scenario engine submits the same four cases — file:// scheme abuse,
internal-host reach, allowlisted-host redirect bypass, and a legitimate preview —
to the secure, vulnerable, and naive applications, then compares what each
returns and stores and prints a per-application verdict.

The engine (``run_matrix`` / ``compute_verdict``) is a pure function of an
injected ``httpx.Client`` and is directly testable without terminal input; the
interactive mode is a thin wrapper over the same ``submit`` primitive.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from dataclasses import dataclass

import httpx

APP_ROLES = ("secure", "vulnerable", "naive")


@dataclass(frozen=True)
class Case:
    name: str
    url: str
    marker: str
    is_attack: bool
    chain: tuple[str, ...]
    decisions: Mapping[str, str]


CASES: tuple[Case, ...] = (
    Case(
        name="file:// scheme abuse",
        url="file:///app/secrets/preview_worker.env",
        marker="PREVIEW_WORKER_TOKEN",
        is_attack=True,
        chain=("file:///app/secrets/preview_worker.env",),
        decisions={
            "secure": "reject: scheme 'file' not allowlisted (no request made)",
            "vulnerable": "no validation: read the local file",
            "naive": "reject: scheme 'file' not allowlisted (submitted-URL check)",
        },
    ),
    Case(
        name="internal-host reach",
        url="http://backoffice.larkspur.internal/service-account",
        marker="service_account_token",
        is_attack=True,
        chain=("http://backoffice.larkspur.internal/service-account",),
        decisions={
            "secure": "reject: host not allowlisted (no request made)",
            "vulnerable": "no validation: fetch the internal host",
            "naive": "reject: host not allowlisted (submitted-URL check)",
        },
    ),
    Case(
        name="allowlisted-host redirect bypass",
        url="http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account",
        marker="service_account_token",
        is_attack=True,
        chain=(
            "http://assets.larkspur.test/r?to=... (host allowlisted)",
            "302 -> http://backoffice.larkspur.internal/service-account (host NOT allowlisted)",
        ),
        decisions={
            "secure": "hop 1 allowed; hop 2 re-validated and rejected before contact",
            "vulnerable": "no validation: follow the redirect to the internal host",
            "naive": "submitted URL allowed; redirect hop NOT re-validated -> internal host",
        },
    ),
    Case(
        name="legitimate preview",
        url="http://assets.larkspur.test/notes/1",
        marker="Fictional preview body for note 1",
        is_attack=False,
        chain=("http://assets.larkspur.test/notes/1 (host allowlisted)",),
        decisions={
            "secure": "allow: scheme and host allowlisted",
            "vulnerable": "allow (no validation)",
            "naive": "allow: submitted URL allowlisted",
        },
    ),
)


@dataclass(frozen=True)
class Observation:
    case: Case
    status: int
    record_created: bool
    returned_marker: bool
    body_excerpt: str


@dataclass(frozen=True)
class AppReport:
    role: str
    base_url: str
    verdict: str
    observations: tuple[Observation, ...]
    history_before: int
    history_after: int


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def submit(client: httpx.Client, base_url: str, token: str, url: str) -> tuple[int, str]:
    """Submit one URL to an application and return (status, response body text)."""
    response = client.post(f"{base_url}/previews", headers=_headers(token), json={"url": url})
    if response.status_code == 201:
        return response.status_code, str(response.json().get("body", ""))
    return response.status_code, response.text


def _history_count(client: httpx.Client, base_url: str, token: str) -> int:
    response = client.get(f"{base_url}/previews", headers=_headers(token))
    if response.status_code != 200:
        return 0
    return len(response.json())


def compute_verdict(attack_observations: list[Observation]) -> str:
    succeeded = [o for o in attack_observations if o.status == 201 and o.returned_marker]
    if not succeeded:
        return "SECURE — all attack submissions rejected"
    if len(succeeded) == len(attack_observations):
        return "VULNERABLE — all attack submissions succeeded"
    return "NAIVE — direct submissions rejected, redirect bypass succeeded"


def run_matrix(client: httpx.Client, apps: Mapping[str, str], token: str) -> list[AppReport]:
    reports: list[AppReport] = []
    for role, base_url in apps.items():
        before = _history_count(client, base_url, token)
        running = before
        observations: list[Observation] = []
        for case in CASES:
            status, body = submit(client, base_url, token, case.url)
            after = _history_count(client, base_url, token)
            observations.append(
                Observation(
                    case=case,
                    status=status,
                    record_created=after > running,
                    returned_marker=case.marker in body,
                    body_excerpt=" ".join(body.split())[:80],
                )
            )
            running = after
        attacks = [o for o in observations if o.case.is_attack]
        reports.append(
            AppReport(
                role=role,
                base_url=base_url,
                verdict=compute_verdict(attacks),
                observations=tuple(observations),
                history_before=before,
                history_after=running,
            )
        )
    return reports


def render(reports: list[AppReport], *, verbose: bool) -> str:
    lines = [
        "fetchjack — SSRF comparison across three applications",
        "=" * 53,
        "",
        "Submitting the same four cases to each application and comparing what",
        "each returns and stores. All hosts, files, and credentials are fictional.",
        "",
    ]
    for report in reports:
        lines.append(f"{report.role} ({report.base_url})")
        lines.append(f"  VERDICT: {report.verdict}")
        lines.append(
            f"  preview history: {report.history_before} -> {report.history_after} record(s)"
        )
        for obs in report.observations:
            if obs.case.is_attack:
                leaked = "yes" if obs.returned_marker else "no"
                tail = f"leaked: {leaked}"
            else:
                tail = "ok" if obs.returned_marker else "unexpected"
            record = "yes" if obs.record_created else "no"
            lines.append(
                f"  - {obs.case.name:<36} status {obs.status:<4} record: {record:<4} {tail}"
            )
            if verbose:
                for hop in obs.case.chain:
                    lines.append(f"        hop: {hop}")
                lines.append(f"        decision: {obs.case.decisions[report.role]}")
                lines.append(f"        body: {obs.body_excerpt!r}")
        lines.append("")
    return "\n".join(lines)


def interactive(client: httpx.Client, apps: Mapping[str, str], token: str) -> None:
    print("Interactive mode. Submit a URL to all three applications; blank line or 'quit' exits.")
    while True:
        try:
            url = input("URL> ").strip()
        except EOFError:
            break
        if url in ("", "quit", "exit"):
            break
        for role, base_url in apps.items():
            status, body = submit(client, base_url, token, url)
            print(f"  [{role:<10}] status={status} body={' '.join(body.split())[:80]!r}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fetchjack",
        description="Compare the secure, vulnerable, and naive preview applications.",
    )
    parser.add_argument("--secure-url", default=os.environ.get("SECURE_URL", "http://secure:8000"))
    parser.add_argument(
        "--vulnerable-url", default=os.environ.get("VULNERABLE_URL", "http://vulnerable:8001")
    )
    parser.add_argument("--naive-url", default=os.environ.get("NAIVE_URL", "http://naive:8002"))
    parser.add_argument("--token", default=os.environ.get("DEMO_TOKEN", "demo-token-ada"))
    parser.add_argument("--verbose", action="store_true", help="show hops, decisions, and bodies")
    parser.add_argument("--interactive", action="store_true", help="submit URLs interactively")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    apps = {
        "secure": args.secure_url,
        "vulnerable": args.vulnerable_url,
        "naive": args.naive_url,
    }
    with httpx.Client(timeout=10.0) as client:
        if args.interactive:
            interactive(client, apps, args.token)
            return 0
        reports = run_matrix(client, apps, args.token)
        print(render(reports, verbose=args.verbose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
