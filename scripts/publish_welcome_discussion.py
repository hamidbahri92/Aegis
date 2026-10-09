#!/usr/bin/env python3
"""Create one GitHub Discussion inviting independent Aegis QEC collaborators.

Runs in a main-only GitHub Actions job with discussions:write permission.
Never creates discussion in any other repository and never publishes duplicates.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "hamidbahri92"
NAME = "Aegis-QEC"
DATABASE_ID = 1052634503
TITLE = "Welcome: learning, reproducibility, and collaboration on Aegis QEC"
BODY = """Aegis QEC is an open-source Python research and learning toolkit for quantum error correction, with a focus on surface codes, Stim detector error models, PyMatching MWPM decoding, and reproducible studies.

We're opening this discussion to students, educators, physicists, decoder developers, hardware researchers, and independent reviewers. **We welcome questions, criticism, reproducibility checks, teaching ideas, and focused contributions.** You do not need to use Aegis already, or to write a new decoder, to participate.

**If you're learning:** Try the [Start Here guide](https://github.com/hamidbahri92/Aegis-QEC/blob/main/docs/START_HERE.md), run one explanation, and tell us what was confusing.

**If you're doing research:** Try to replicate one small experiment, including the seeds, software versions, raw artifacts, and uncertainty. The [independent replication issue](https://github.com/hamidbahri92/Aegis-QEC/issues/51) is a good entry point.

**If you're developing or teaching:** Review the documentation, correct unclear scientific claims, propose interoperable examples, or help make the output more accessible. [First-user feedback](https://github.com/hamidbahri92/Aegis-QEC/issues/50) is especially useful.

Aegis builds *around* tools such as [Stim](https://github.com/quantumlib/Stim) and [PyMatching](https://github.com/oscarhiggott/PyMatching); it is not a replacement or a claim of universal QEC coverage. Our long-term hope is to develop, with collaborators, a more unified educational and research resource where experiments are easy to understand, reproduce, and challenge.

What was the last QEC concept, experiment, or decoder integration you wished was easier to understand or reproduce? We'd love to learn from your experience. Please do not share credentials or confidential hardware data.
"""


def category_id(categories: list[dict]) -> str:
    """Prefer a conversational category; never create one in an unrelated repo."""
    for wanted in ("general", "ideas", "q&a"):
        for cat in categories:
            if cat.get("name", "").casefold() == wanted and cat.get("id"):
                return cat["id"]
    if not categories:
        raise RuntimeError("No GitHub Discussion categories exist")
    if categories[0].get("id"):
        return categories[0]["id"]
    raise RuntimeError("GitHub Discussion category missing id")


def find_existing(discussions: list[dict]) -> str | None:
    """Avoid duplicate welcome posts when the workflow is rerun."""
    for item in discussions:
        if item.get("title") == TITLE:
            return item.get("url")
    return None


def graphql(token: str, query: str, variables: dict) -> dict:
    req = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Aegis-QEC-welcome-discussion",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except HTTPError as exc:
        raise RuntimeError(
            f"GitHub GraphQL returned HTTP {exc.code}; check workflow Discussions permission."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("GitHub GraphQL connection failed") from exc
    if result.get("errors"):
        # Do not print full server responses that might expose authorization context.
        raise RuntimeError("GitHub GraphQL returned errors; check category and token permissions")
    if "data" not in result:
        raise RuntimeError("GitHub GraphQL result has no data")
    return result["data"]


def main() -> int:
    if os.environ.get("GITHUB_REPOSITORY") != f"{OWNER}/{NAME}":
        raise RuntimeError("Refusing to publish in a different GitHub repository")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("Welcome discussion may be published only from main")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GitHub Actions token is missing")

    lookup = """query($owner:String!,$repo:String!){
      repository(owner:$owner,name:$repo) {
        id databaseId nameWithOwner
        discussionCategories(first:25) { nodes { id name } }
        discussions(first:100) { nodes { title url } }
      }
    }"""
    data = graphql(token, lookup, {"owner": OWNER, "repo": NAME})
    record = data.get("repository") or {}
    if (
        record.get("databaseId") != DATABASE_ID
        or record.get("nameWithOwner") != f"{OWNER}/{NAME}"
        or not record.get("id")
    ):
        raise RuntimeError("Repository identity verification failed")
    existing = find_existing(
        (record.get("discussions") or {}).get("nodes") or []
    )
    if existing:
        print(f"ALREADY EXISTS: {existing}")
        return 0
    cats = (record.get("discussionCategories") or {}).get("nodes") or []
    cid = category_id(cats)
    mutation = """mutation($repositoryId:ID!,$categoryId:ID!,$title:String!,$body:String!){
      createDiscussion(input:{
        repositoryId:$repositoryId, categoryId:$categoryId, title:$title, body:$body
      }) { discussion { title url repository { nameWithOwner databaseId } } }
    }"""
    created = graphql(
        token,
        mutation,
        {
            "repositoryId": record["id"],
            "categoryId": cid,
            "title": TITLE,
            "body": BODY,
        },
    )
    discussion = (created.get("createDiscussion") or {}).get("discussion") or {}
    if (
        discussion.get("title") != TITLE
        or not discussion.get("url", "").startswith(
            f"https://github.com/{OWNER}/{NAME}/discussions/"
        )
        or (discussion.get("repository") or {}).get("databaseId") != DATABASE_ID
    ):
        raise RuntimeError("Discussion creation returned an unverified result")
    print(f"SUCCESS: {discussion['url']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
