#!/usr/bin/env python3
"""Rename the existing Aegis GitHub repository, never create a second repository.

Requires the already-configured, repository-scoped Actions secret AEGIS.
Run ONLY from protected main using the explicit rename-to-Aegis-QEC workflow choice.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "hamidbahri92"
OLD_NAME = "Aegis"
NEW_NAME = "Aegis-QEC"
REPO_ID = 1052634503
EXPECTED_OLD = f"{OWNER}/{OLD_NAME}"
EXPECTED_NEW = f"{OWNER}/{NEW_NAME}"
API_ROOT = "https://api.github.com/repos"


def validate_identity(record: dict, expected_full_name: str) -> None:
    """Fail closed if either the repository ID or its owner/name is wrong."""
    if record.get("id") != REPO_ID or record.get("full_name") != expected_full_name:
        raise RuntimeError(
            "GitHub repository identity did not match the existing Aegis repository. "
            "Refusing to rename anything."
        )


def request(name: str, method: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Aegis-QEC-canonical-repository-rename",
        "Authorization": f"Bearer {token}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{API_ROOT}/{OWNER}/{name}", headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        # Credentials and raw API error bodies must not be printed in workflow logs.
        raise RuntimeError(
            f"GitHub API {method} to repository {name} returned HTTP {exc.code}; "
            "verify the AEGIS secret is valid and has Administration: Read and write."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("GitHub API request failed; no safe completion verdict.") from exc


def check_sources_prepared() -> None:
    """Rename only after links and workflows are staged for the new canonical URL."""
    required = {
        "README.md": "github.com/hamidbahri92/Aegis-QEC",
        "pyproject.toml": "github.com/hamidbahri92/Aegis-QEC",
        "CITATION.cff": "github.com/hamidbahri92/Aegis-QEC",
        ".github/workflows/discoverability.yml": "hamidbahri92/Aegis-QEC",
        ".github/repository-settings.json": '"repository_name": "Aegis-QEC"',
    }
    for path, marker in required.items():
        if marker not in Path(path).read_text(encoding="utf-8"):
            raise RuntimeError(f"Migration preflight failed: {path} is not prepared.")


def main() -> int:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("Repository rename can only run on main.")
    source = os.environ.get("GITHUB_REPOSITORY", "")
    if source not in {EXPECTED_OLD, EXPECTED_NEW}:
        raise RuntimeError("Refusing to rename a repository outside the expected identity.")
    if os.environ.get("AEGIS_RENAME_CONFIRM") != NEW_NAME:
        raise RuntimeError("Explicit rename confirmation is missing.")
    check_sources_prepared()

    token = os.environ.get("AEGIS_REPO_ADMIN_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Actions secret AEGIS is missing. It must contain a GitHub token "
            "with Administration: Read and write for this repository."
        )
    current_name = source.split("/", 1)[1]
    current = request(current_name, "GET", token)
    validate_identity(current, source)

    if current_name == NEW_NAME:
        print(f"ALREADY RENAMED: https://github.com/{EXPECTED_NEW}")
        return 0

    print(f"Renaming existing GitHub repository ID {REPO_ID}: {OLD_NAME} -> {NEW_NAME}")
    result = request(OLD_NAME, "PATCH", token, {"name": NEW_NAME})
    validate_identity(result, EXPECTED_NEW)
    print("GitHub accepted the repository rename; verifying canonical endpoint.")

    for attempt in range(4):
        try:
            verified = request(NEW_NAME, "GET", token)
            validate_identity(verified, EXPECTED_NEW)
            print(f"SUCCESS: https://github.com/{EXPECTED_NEW}")
            print(
                "NEXT RELEASE: Confirm PyPI Trusted Publisher repository identity "
                "uses Aegis-QEC. No release or PyPI publication was triggered."
            )
            return 0
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(2)
    raise RuntimeError("Unable to independently verify repository rename.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
