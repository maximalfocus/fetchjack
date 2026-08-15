"""The published documentation is part of the deliverable, so it is asserted like the code.

These checks are deliberately coarse: they prove the required subjects are covered, that the
licensing is consistent, and that nothing which belongs to private planning has crept in. They
cannot judge whether the prose is any good.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WALKTHROUGH = (ROOT / "docs" / "WALKTHROUGH.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
CONTRIBUTING = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
SECURITY = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
LICENSE = (ROOT / "LICENSE").read_text(encoding="utf-8")

# The two narrative documents, which must stay wholly fictional.
DOCUMENTS = {"docs/WALKTHROUGH.md": WALKTHROUGH, "README.md": README}

# Everything a visitor to the public repository can read.
PUBLIC_DOCUMENTS = {
    "docs/WALKTHROUGH.md": WALKTHROUGH,
    "README.md": README,
    "CONTRIBUTING.md": CONTRIBUTING,
    "SECURITY.md": SECURITY,
}


def flowing(text: str) -> str:
    """Collapse Markdown wrapping so a sentence can be matched across line breaks."""
    return " ".join(text.replace(">", " ").split()).lower()


def test_the_license_is_the_canonical_mit_text_with_accurate_attribution() -> None:
    assert LICENSE.startswith("MIT License")
    assert "Copyright (c) 2026 maximalfocus" in LICENSE
    for clause in (
        "Permission is hereby granted, free of charge",
        "The above copyright notice and this permission notice shall be included in all",
        'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND',
    ):
        assert clause in LICENSE


def test_package_metadata_declares_the_same_spdx_license() -> None:
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'license = "MIT"' in metadata
    assert 'license-files = ["LICENSE"]' in metadata


def test_the_readme_points_at_the_license_and_the_two_policies() -> None:
    for link in ("(LICENSE)", "(CONTRIBUTING.md)", "(SECURITY.md)"):
        assert link in README


@pytest.mark.parametrize(
    "statement",
    [
        "educational",
        "intentionally vulnerable",
        "Docker Compose",
        "no hosted service",
        "must never be deployed",
        "production-readiness claim",
    ],
)
def test_the_readme_states_the_public_operating_boundary(statement: str) -> None:
    assert statement in " ".join(README.replace(">", " ").split())


def test_the_readme_no_longer_reads_as_pre_publication() -> None:
    flowed = flowing(README)

    for phrase in (
        "under private development",
        "private implementation",
        "no license is granted",
        "delivered so far",
        "one remaining slice",
    ):
        assert phrase not in flowed, f"README still reads as pre-publication: {phrase}"


def test_the_security_policy_separates_the_taught_flaw_from_real_ones() -> None:
    flowed = flowing(SECURITY)

    assert "do not report these" in flowed
    assert "the flaw in this repository is the product" in flowed
    # ...and names what a genuine finding would look like.
    assert "escapes the demo container" in flowed
    assert "not allowlisted" in flowed
    assert "secure" in flowed


def test_the_security_policy_gives_a_non_public_reporting_path() -> None:
    assert "security/advisories/new" in SECURITY
    assert "private vulnerability reporting" in flowing(SECURITY)
    assert "do not open a public issue" in flowing(SECURITY)


def test_contribution_guidance_covers_the_gate_and_the_safety_rules() -> None:
    flowed = flowing(CONTRIBUTING)

    assert "docker compose run --rm --build verify" in CONTRIBUTING
    assert "allow_vulnerable_demo=true" in flowed
    assert "everything stays fictional" in flowed
    assert "nothing reaches the public internet" in flowed
    assert "no deployment" in flowed


@pytest.mark.parametrize("document", sorted(PUBLIC_DOCUMENTS))
def test_no_public_document_promises_support_or_production_readiness(document: str) -> None:
    flowed = flowing(PUBLIC_DOCUMENTS[document])

    for promise in (
        "production-ready",
        "production ready",
        "supported release",
        "response time of",
        "within 24 hours",
        "service level agreement",
        "sla",
    ):
        assert promise not in flowed, f"{document} promises: {promise}"


@pytest.mark.parametrize("document", sorted(PUBLIC_DOCUMENTS))
def test_no_public_document_references_private_planning_material(document: str) -> None:
    flowed = flowing(PUBLIC_DOCUMENTS[document])

    # Deliberately generic: naming the private companion here would make this guard the
    # disclosure it exists to prevent. The bare terms catch any reference to a requirements
    # document, a progress tracker, a local path, or a private companion repository.
    for term in (
        "prd",
        "progress.md",
        "/users/",
        "private repository",
        "companion repository",
        "requirements document",
        "series roadmap",
    ):
        assert term not in flowed, f"{document} references private material: {term}"


@pytest.mark.parametrize("document", sorted(PUBLIC_DOCUMENTS))
def test_the_only_external_host_referenced_is_this_repository(document: str) -> None:
    allowed = (
        "https://github.com/maximalfocus/fetchjack/",
        "http://127.0.0.1:",
        "http://localhost:",
        # The demo's own in-network fixtures, proven fictional by the guard below.
        "http://assets.larkspur.test",
        "http://backoffice.larkspur.internal",
    )

    for url in re.findall(r"https?://[^\s)>\"'`]+", PUBLIC_DOCUMENTS[document]):
        assert url.startswith(allowed), f"{document} links off to a third party: {url}"


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
def test_documented_hosts_stay_inside_the_fictional_fixture_domains(document: str) -> None:
    text = DOCUMENTS[document]

    assert "assets.larkspur.test" in text
    assert "backoffice.larkspur.internal" in text
    for real_looking in (".com", ".net", ".org", ".io"):
        assert real_looking not in text, f"{document} names a real-looking domain: {real_looking}"
