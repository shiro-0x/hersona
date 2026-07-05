# Release checklist

> Written in response to an external review noting "rough release
> operations" (a semver rollback sequence, a publish failure, README/About
> drift — all honestly recorded in `CHANGELOG.md` rather than hidden, but
> avoidable with a checklist). See
> [`docs/reviews/2026-07-04-external-review-response.md`](./reviews/2026-07-04-external-review-response.md) §P3-1.

This is a **manual checklist** — some steps (bumping `pyproject.toml`,
moving the `CHANGELOG.md` heading, tagging) are judgment calls that aren't
automated. `scripts/release_check.py` automates everything that *can* be
checked mechanically (the same gates CI runs), so you can catch a broken
release before pushing a tag instead of after.

## 1. Run the mechanical gates locally

```bash
python scripts/release_check.py            # runs ruff, validate.py, build_site.py --check,
                                             # check_readme_counts.py, gen_checksums.py --check, pytest
python scripts/release_check.py --skip-pytest  # faster loop while iterating; pytest still runs in CI
```

Fix anything this reports before continuing. If you changed
`attributes/**/*.yaml`, make sure you already ran
`python scripts/build_site.py` and `python scripts/gen_checksums.py` (not
just `--check`) to regenerate the data files — `release_check.py` only
verifies they're *not stale*, it doesn't regenerate them for you.

## 2. Move the CHANGELOG heading

`CHANGELOG.md` accumulates everything under `## [Unreleased]`. Rename that
heading to `## [X.Y.Z] - YYYY-MM-DD` and add a fresh empty
`## [Unreleased]` above it for whatever comes next. Follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) section ordering
(Added / Changed / Fixed / etc.) — see existing entries for the house style.

## 3. Bump `pyproject.toml`

```toml
[project]
version = "X.Y.Z"
```

Follow the compatibility policy in
[`docs/PUBLIC_API.md`](./PUBLIC_API.md#互換性ポリシー) /
[`PUBLIC_API.en.md`](./PUBLIC_API.en.md#compatibility-policy): removing a
public symbol or attribute is major, additive changes are minor, data/
wording fixes are patch.

> **Known history**: 2026-06-17 saw a semver rollback sequence
> (v1.3.0 → v0.2.0 → v1.4.0) due to a user-directed correction — recorded
> honestly in `CHANGELOG.md` rather than erased. If a mistake like this
> happens again, record it the same way instead of rewriting history.

## 4. Cross-check attribute counts (can't be automated end-to-end)

- `python scripts/check_readme_counts.py` already ran in step 1 and checks
  `README.md` / `README.ja.md` against `tests/catalog_counts.py`.
- **GitHub's "About" field (repo description) is not covered by any script**
  — there is no API access for it in this project's tooling. If the
  attribute count changed this release, update it manually:
  **Settings → General → Description**, or the gear icon next to "About"
  on the repo homepage.

## 5. Skill version (if `skills/hersona/SKILL.md` changed)

`tests/test_skill_versions.py` only checks the `version:` front-matter is
valid SemVer, not that it was bumped. If you changed the skill's behavior
or documented surface this release, bump it per
`CONTRIBUTING.md` ("スキルのバージョン管理"): patch for compatible fixes,
minor for an expanded input/output contract, major for a breaking change.

## 6. Tag and push

```bash
git tag vX.Y.Z
git push --tags
```

This triggers `.github/workflows/publish.yml`. **`fetch-depth: 0`** in that
workflow means it always builds the tag's actual tip commit — but if you
force-pushed a tag on top of a previous one, PyPI will still reject the
re-upload (`400 File already exists`); PyPI package versions are immutable
per version string, tags are not. If you need to fix something after
tagging, bump to a new patch version instead of re-pushing the same tag.

## 7. Watch the release build

Check the `publish.yml` run in GitHub Actions:

- `build` job: wheel/sdist build, the in-workflow smoke test
  (`from hersona.core import render_blend, available_attributes`), and
  build provenance attestation (`actions/attest-build-provenance`).
- `publish` job: PyPI upload via Trusted Publishing (OIDC) — no manual
  token needed. If this fails with an auth error, the PyPI-side "Trusted
  Publisher" configuration (see the comment at the top of `publish.yml`)
  may need re-checking; it's tied to the exact workflow filename and
  environment name.

## 8. Verify the published package

```bash
uv venv /tmp/release-smoke && uv pip install --python /tmp/release-smoke/bin/python hersona==X.Y.Z
/tmp/release-smoke/bin/hersona list | tail -1   # should show the expected total count
```

Optionally verify the build provenance attestation:

```bash
gh attestation verify dist/hersona-X.Y.Z-py3-none-any.whl --owner shiro-0x
```

## 9. (Optional) Create a GitHub Release

Tagging alone is sufficient for PyPI publishing. If you also want a GitHub
Release entry (for visibility / release notes), create one from the tag
and paste in the corresponding `CHANGELOG.md` section.
