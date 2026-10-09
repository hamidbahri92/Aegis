# Publishing Aegis QEC to PyPI

This guide describes the repository's tagged-release or reviewed-main release-request process and its GitHub OIDC connection to PyPI Trusted Publishing. It is for maintainers; package installation and use are covered in the project README.

## Trusted Publisher identity

Before merging the Trusted Publishing workflow or creating a release tag, configure a publisher for the existing PyPI project `aegis-qec`. In the PyPI project settings, add a GitHub Actions Trusted Publisher with these exact values:

| PyPI field | Value |
| --- | --- |
| PyPI project | `aegis-qec` |
| Owner | `hamidbahri92` |
| Repository | `Aegis-QEC` |
| Workflow filename | `release-pypi.yml` |
| Environment | Leave blank |

The workflow filename is the basename of `.github/workflows/release-pypi.yml`. The environment must remain unset: the workflow does not declare a GitHub Actions environment. The repository was previously named `Aegis`. After renaming it to `Aegis-QEC`, the PyPI Trusted Publisher identity must be configured to match **`Aegis-QEC`** before the next release. The 1.2.0 release used a separate API-token fallback because OIDC Trusted Publishing was not accepted. Confirm a future OIDC-backed publication before removing any working fallback credential. If the repository owner, repository name, workflow filename, or environment changes later, update the Trusted Publisher record to match before publishing.

This setting belongs to the PyPI project and cannot be created by a repository change. A green pull-request CI run does not prove that it exists.

## What the release workflow does

A release starts when a tag matching `v*.*.*` is pushed, or when main is updated with `.github/RELEASE_REQUEST` (in which case the workflow resolves or creates the matching immutable tag). The `build` job checks out the tagged source, builds the wheel and source distribution, runs Twine metadata checks, installs and smoke-tests the wheel, and verifies that the tag version equals the version read from the installed `aegis-qec` package metadata. It then uploads those validated distributions as a short-lived workflow artifact.

The dependent `publish` job downloads that artifact and calls `pypa/gh-action-pypi-publish`. It has the workflow's only `id-token: write` permission. The build job has no OIDC permission. The current publishing job attempts OIDC Trusted Publishing first, but if that action fails it has a legacy Twine upload fallback using the `PYPI_API_TOKEN` Actions secret. A successful overall workflow does not establish that OIDC worked; inspect the publishing steps and PyPI release page.

A pull-request check exercises the repository's ordinary CI but does not request a PyPI OIDC token or publish a package. The first end-to-end proof is a successful tagged release after the Trusted Publisher has been configured.

## Release procedure

First confirm the Trusted Publisher identity above in PyPI, then merge the reviewed workflow change. Choose a new release version, update `[project].version` in `pyproject.toml`, and make sure the package version and release notes are ready on the commit to be released. Push a matching version tag such as `v1.2.0`; the tag must match the package metadata exactly after removing its leading `v`.

Watch the `Release (PyPI)` workflow in GitHub Actions. Do not treat a successful build job as a published release: confirm that the publish job also succeeds and that the new version appears on the `aegis-qec` PyPI project page. If the publish job reports an OIDC or publisher-identity mismatch, check the five PyPI fields above, especially the workflow filename and the blank environment. The existing token fallback should not be treated as evidence that OIDC Trusted Publishing is correctly configured.

## Remove the legacy credential

The current default-branch workflow still references `PYPI_API_TOKEN` as a fallback. After a future release has verifiably succeeded through OIDC Trusted Publishing and the package appears on PyPI, plan and review removal of the fallback and revoke its corresponding API token in PyPI. Removing the GitHub secret does not revoke the PyPI token, and revoking the PyPI token does not remove the GitHub secret; perform and verify both cleanup steps.

Do not put a token value in this repository, its issues, pull requests, workflow logs, or this guide. If an OIDC release cannot complete, diagnose and fix the publisher identity or workflow permissions. Do not silently add or broaden long-lived credentials.
