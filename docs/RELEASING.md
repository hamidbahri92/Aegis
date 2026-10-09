# Publishing Aegis QEC to PyPI

This maintainer guide describes the release workflow currently implemented in `.github/workflows/release-pypi.yml`. Normal installation instructions are in the project README.

## PyPI Trusted Publisher identity

For the existing PyPI project `aegis-qec`, open the project's **Manage → Publishing** settings and check/add its GitHub Actions Trusted Publisher:

| PyPI field | Exact value |
| --- | --- |
| Project | `aegis-qec` |
| Owner | `hamidbahri92` |
| Repository | `Aegis` |
| Workflow filename | `release-pypi.yml` |
| Environment | Leave blank (unset) |

The workflow path is `.github/workflows/release-pypi.yml`. The publishing job requests `id-token: write` and does **not** declare a GitHub Actions environment. A nonblank environment configured on PyPI will not match these claims. Check capitalization, owner, repository, and workflow filename exactly.

This is a setting on the **PyPI project**, not in this GitHub repository. Repository commits cannot register or repair it. See [PyPI's existing-project setup](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) and [invalid-publisher troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/).

## Actual release triggers and flow

`Release (PyPI)` runs on:

- A pushed tag matching `v*.*.*`; **or**
- A push to `main` that changes `.github/RELEASE_REQUEST`.

The resolver compares the requested version (the tag without `v`, or the contents of `.github/RELEASE_REQUEST`) with `[project].version` in `pyproject.toml`. A main-branch release request creates an annotated `v<version>` tag on the reviewed commit if the tag does not yet exist. When the tag already exists, the workflow reuses it rather than moving it. The build job checks out that tag and builds, checks with Twine, installs, and smoke-tests the wheel and source distribution; the resulting distributions are kept as a short-lived Actions artifact.

The publish job tries `pypa/gh-action-pypi-publish@release/v1` using GitHub OIDC first. **As currently implemented, if OIDC publishing fails, it invokes Twine using the existing `PYPI_API_TOKEN` secret as a fallback.** Therefore a green overall release run does not prove that Trusted Publishing worked. Inspect the "Publish with PyPI Trusted Publishing" step **and** the fallback step, not just the job conclusion. The GitHub Release job runs only after the publish job finishes successfully, then attaches the validated wheel and source distribution.

Ordinary pull-request CI does not test PyPI's OIDC publisher configuration. The separate TestPyPI workflow is manual and currently uses `TEST_PYPI_API_TOKEN`; it does not establish production PyPI Trusted Publishing readiness.

## Verified release 1.2.0 evidence (October 8, 2026)

Release commit `1b62b49f460fad2a6497448b9820c0d1f1237503` on `main` triggered [the release run](https://github.com/hamidbahri92/Aegis/actions/runs/37752034855) and [the CI run](https://github.com/hamidbahri92/Aegis/actions/runs/37752034901). Both completed successfully. The annotated tag `v1.2.0` resolves to that commit. The [GitHub Release](https://github.com/hamidbahri92/Aegis/releases/tag/v1.2.0) was published with `aegis_qec-1.2.0-py3-none-any.whl` and `aegis_qec-1.2.0.tar.gz` attached.

In the [publishing job](https://github.com/hamidbahri92/Aegis/actions/runs/37752034855/job/113227569628), PyPI rejected OIDC with `invalid-publisher: valid token, but no corresponding publisher`. The recorded OIDC claims were `repository=hamidbahri92/Aegis`, `workflow_ref=hamidbahri92/Aegis/.github/workflows/release-pypi.yml@refs/heads/main`, and an **absent** environment. The token-based Twine fallback then successfully uploaded both files to PyPI and printed `https://pypi.org/project/aegis-qec/1.2.0/`. This confirms the fallback publish, **not** an OIDC-backed publish. Confirm package visibility independently in the [PyPI project](https://pypi.org/project/aegis-qec/1.2.0/) or its [version JSON](https://pypi.org/pypi/aegis-qec/1.2.0/json).

Do **not** recreate or move `v1.2.0`, rebuild and republish this existing version under the same filename, or change version metadata merely to fix the OIDC publisher identity.

## Recover OIDC for a future release

1. In PyPI's project Publishing settings, reconcile the publisher against the five exact fields above. An `invalid-publisher` response may mean the publisher is missing or its stored claims do not match; the GitHub error alone does not distinguish these cases.
2. Keep `id-token: write` on the narrowly scoped publishing job. There is no evidence that changing repository permissions, dependency versions, or release tags would fix this identity rejection. Do not expose the long-lived token in logs or commits.
3. At the **next legitimate version**, observe the Trusted Publishing step succeed without entering the token fallback. Confirm the corresponding package/version appears in PyPI. PyPI's per-file "Uploaded using Trusted Publishing" field provides additional independent evidence.
4. **Only after OIDC publishing has been proven**, remove the `PYPI_API_TOKEN` fallback from the workflow, delete the GitHub Actions secret, and revoke the corresponding token in PyPI. Removing the GitHub secret does not revoke the token. Treat these as separate verified operations.

The existing fallback is documented here to avoid misreporting the 1.2.0 run. OIDC remains the intended publishing path; a security-hardening change to remove fallback should be reviewed separately rather than bundled with a documentation correction.
