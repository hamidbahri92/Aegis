#!/usr/bin/env python3
"""Safely update the public Aegis QEC GitHub repository metadata.

GitHub's GITHUB_TOKEN cannot change repository description, homepage, or topics.
Apply mode requires a fine-grained admin token stored as the Actions secret AEGIS.
Preview mode reads public metadata without requiring that secret.
"""

from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "hamidbahri92"
REPO = os.environ.get("GITHUB_REPOSITORY", f"{OWNER}/Aegis").partition("/")[2]
REPO_ID = 1052634503
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
DESCRIPTION = (
    "Aegis QEC — Open-source quantum error correction for surface codes: "
    "Stim/PyMatching MWPM decoding, noise simulation, benchmarking, "
    "and reproducible research."
)
HOMEPAGE = "https://pypi.org/project/aegis-qec/"
DISCOVERY_TOPICS = (
    "quantum-error-correction",
    "quantum-computing",
    "qec",
    "surface-code",
    "surface-codes",
    "fault-tolerant-quantum-computing",
    "quantum-information",
    "quantum-decoding",
    "error-correction",
    "mwpm",
    "pymatching",
    "quantum-simulation",
    "python",
    "research-software",
    "reproducible-research",
)


def merged_topics(current: list[str]) -> list[str]:
    """Never discard previously configured topics; reject unsafe overflows."""
    topics = list(dict.fromkeys([*current, *DISCOVERY_TOPICS]))
    if len(topics) > 20:
        raise ValueError(
            f"Would exceed GitHub's 20-topic limit ({len(topics)}). "
            "Review topics manually before applying."
        )
    for topic in topics:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", topic):
            raise ValueError(f"Invalid GitHub topic: {topic!r}")
    return topics


def github_api(method: str, path: str, token: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Aegis-QEC-discoverability-workflow",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    url = f"{API}{path}"
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Do not print request headers, credentials, or arbitrary API response bodies.
        raise RuntimeError(
            f"GitHub API {method} {path} returned HTTP {exc.code}. "
            "Verify repository permissions and token configuration."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"GitHub API {method} {path} could not be reached."
        ) from exc


def main() -> int:
    mode = os.environ.get("AEGIS_DISCOVERABILITY_MODE", "preview")
    if mode not in {"preview", "apply"}:
        raise ValueError("Mode must be preview or apply.")
    actual_repo = os.environ.get("GITHUB_REPOSITORY", f"{OWNER}/{REPO}")
    if actual_repo not in {f"{OWNER}/Aegis", f"{OWNER}/Aegis-QEC"}:
        raise RuntimeError(
            f"Refusing to change metadata outside the canonical Aegis QEC repository: {actual_repo}"
        )

    read_token = os.environ.get("GITHUB_TOKEN", "")
    repo_info = github_api("GET", "", read_token)
    if repo_info.get("id") != REPO_ID or repo_info.get("full_name") != f"{OWNER}/{REPO}":
        raise RuntimeError("Repository identity changed; refusing metadata mutation.")
    old_topics = github_api("GET", "/topics", read_token).get("names", [])
    topics = merged_topics(old_topics)
    current = {
        "description": repo_info.get("description") or "",
        "homepage": repo_info.get("homepage") or "",
        "topics": old_topics,
    }
    proposed = {"description": DESCRIPTION, "homepage": HOMEPAGE, "topics": topics}
    print(f"Aegis QEC discoverability — {mode} (repository id {REPO_ID})")
    print("Current:", json.dumps(current, ensure_ascii=False, indent=2))
    print("Proposed:", json.dumps(proposed, ensure_ascii=False, indent=2))

    if mode == "preview":
        print("PREVIEW ONLY: no repository settings were changed.")
        return 0

    admin_token = os.environ.get("AEGIS_REPO_ADMIN_TOKEN", "")
    if not admin_token:
        raise RuntimeError(
            "Apply mode requires repository Actions secret AEGIS. "
            "The token must be saved as a secret, not merely named Aegis in token settings. "
            "Create a fine-grained PAT limited to this repository, with "
            "Administration: Read and write; store it only as a GitHub Actions secret."
        )

    if (
        current["description"] != DESCRIPTION
        or current["homepage"] != HOMEPAGE
    ):
        github_api(
            "PATCH",
            "",
            admin_token,
            {"description": DESCRIPTION, "homepage": HOMEPAGE},
        )
        print("Updated repository description and website.")
    if set(old_topics) != set(topics):
        github_api("PUT", "/topics", admin_token, {"names": topics})
        print("Updated repository topics while preserving existing topics.")

    verified = github_api("GET", "", read_token)
    verified_topics = github_api("GET", "/topics", read_token).get("names", [])
    if (
        verified.get("description") != DESCRIPTION
        or verified.get("homepage") != HOMEPAGE
        or set(verified_topics) != set(topics)
    ):
        raise RuntimeError(
            "Readback did not match requested settings; "
            "inspect the log and safely rerun apply after checking the partial state."
        )
    print("SUCCESS: description, website, and topics verified from GitHub.")
    print(f"Repository: https://github.com/{OWNER}/{REPO}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
