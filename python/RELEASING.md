# Releasing `orgdatacore`

Releases are **tag-driven**. Pushing a `python-v*` tag builds, gates, and
publishes to PyPI via Trusted Publishing — there is no manual upload step and no
stored PyPI token.

This covers the **Python** package only. It lives in `python/` inside the
`cyborg-data` monorepo (the Go module is released separately). Python release
tags are therefore prefixed **`python-v`** so they never collide with Go tags or
the legacy `v0.1.0` tag.

## Versioning

The package version comes from the git tag (`hatch-vcs`): tag `python-v2.0.0`
publishes `orgdatacore` `2.0.0`. There is **no version string to edit** in
`pyproject.toml` — the tag is the single source of truth, and
`orgdatacore.__version__` reads it back from the installed package metadata.

`orgdatacore` follows SemVer over its public API. It consumes the
`orgindex-schema` contract; the pin in `pyproject.toml`
(`orgindex-schema>=0.1.0,<0.2.0`) is what guards compatibility with that contract.

## Cutting a release

1. Ensure `main` is green (Prow CI on the commit you intend to release).
2. Update `python/CHANGELOG.md`: move `Unreleased` items under the new version and
   set its date.
3. Tag and push a **signed** tag on that commit (push access to `upstream`
   required):
   ```bash
   git tag -s python-v2.0.0 -m python-v2.0.0
   git push upstream python-v2.0.0
   ```
   (Unsigned `git tag -a` also works — the workflow does not verify signatures.)
4. The `Release` workflow builds, runs the gate (`ruff` + `mypy` + `pytest`), then
   **pauses at the `pypi` environment for a required-reviewer approval**.
5. **Approve the deployment:** Actions → the release run → **Review deployments** →
   approve `pypi` (a reviewer who is not the tag author). It then publishes to
   PyPI (Trusted Publishing + attestations) and creates the GitHub Release.
   Nothing publishes until this approval.

## Pre-release dry run

Tag a pre-release to publish to **TestPyPI** only — no approval gate, no GitHub
Release:

```bash
git tag -s python-v2.0.0rc1 -m python-v2.0.0rc1
git push upstream python-v2.0.0rc1
```

Then smoke-test the install from TestPyPI before the final tag (it pulls
`orgindex-schema` from real PyPI):

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ "orgdatacore==2.0.0rc1"
```

## One-time setup (maintainers)

Publishing uses **PyPI Trusted Publishing (OIDC)**, so these are configured once in
the web UIs — they cannot be scripted:

- **PyPI Trusted Publisher** for project `orgdatacore`:
  - Repository: `openshift-eng/cyborg-data`
  - Workflow: `release.yml`
  - Environment: `pypi`

  If the project does not exist on PyPI yet, add it as a **pending publisher**
  (PyPI → *Your projects* → *Publishing*) with the same values; the first
  successful run creates the project.
- **TestPyPI Trusted Publisher**: same values, environment `testpypi`.
- **GitHub Environments** (repo *Settings → Environments*):
  - `pypi` — add **required reviewers** and restrict deployment tags to
    `python-v*`, so every production publish is human-approved.
  - `testpypi` — no reviewers needed.
- After the first publish, **add co-owners on PyPI** (project → *Manage →
  Collaborators*) so the project is not single-owner.
