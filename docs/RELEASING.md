# Releasing

## Policy

Releases are built from public source, not from a maintainer's installed
workspace or an earlier ZIP. A version with a pre-release suffix is published
as a GitHub pre-release. Do not tag, push a tag, or publish when any quality
gate fails.

## Version contract

The single canonical machine-readable version source is:

`PACKAGE_MANIFEST.json`

For the current manifest version, the assets are:

```text
minius_codex_lab-workspace-v1.1.0-beta.1.zip
minius_codex_lab-workspace-v1.1.0-beta.1.zip.sha256
minius_codex_lab-workspace-v1.1.0-beta.1.spdx.json
```

## Pre-tag checklist

1. Confirm the working tree and branch are correct.
2. Confirm derived versions in `pyproject.toml`, README, changelog and release
   notes; the validator compares them with `PACKAGE_MANIFEST.json`.
3. Review the release allowlist and all runtime template changes.
4. Run:

```bash
ruff check .
ruff format --check .
python3 scripts/validate_workspace.py --mode upstream
python3 scripts/check_repo_safety.py --profile upstream-public
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tools/verifiable_document/tests -v
python3 -m pytest
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
python3 scripts/build_release.py
python3 scripts/build_release.py --check-reproducibility
```

5. Verify the ZIP name, size, SHA-256, manifest, clean extraction, and
   distribution-safety result.
6. Commit the release source and wait for successful CI on `main`.

## Tag and publication

Create an annotated tag only after CI succeeds:

```bash
version="$(python3 -c 'import json; print(json.load(open("PACKAGE_MANIFEST.json"))["version"])')"
git tag -a "v$version" -m "Release $version"
git push origin "v$version"
```

The tag-triggered `.github/workflows/release.yml` repeats all gates, rebuilds
all assets from that tag, and creates or updates the single release for the
tag. It marks suffix versions as pre-releases and creates GitHub artifact
attestations for the ZIP and SPDX SBOM.

Do not run `gh release create` in parallel. The workflow is the publication
owner.

## Release notes

The tag must have a matching file at `docs/releases/<tag>.md` containing:

- stability status;
- installation and SHA verification;
- non-affiliation and legal-review notice;
- principal skills/features;
- known limitations;
- manual-upgrade warning.

## Failure handling

- CI failure: fix with a new commit and ordinary push; do not rewrite history.
- Failure before tag push: leave the tag unpushed or delete only the local tag.
- Failure after tag push but before release: fix the workflow/source with a new
  version; do not move an already published tag.
- Release asset mismatch or non-reproducibility: stop publication and preserve
  logs/checksums for diagnosis.
- Never substitute a locally edited ZIP.
