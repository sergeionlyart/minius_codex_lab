# Changelog

All notable public changes are documented here. The project follows Semantic
Versioning while pre-release compatibility remains explicitly limited.

## [Unreleased]

## [1.1.0-beta.1] - 2026-07-15

### Added

- Added the `format-monitoring-report` skill with a machine-readable visual
  contract, exact seven-section skeleton, safe authoring guidance, and
  synthetic contract tests. The skill formats approved content only and
  explicitly excludes research methodology and legal analysis.

### Changed

- Raised the exact public skill inventory from 12 to 13 across validation,
  runtime probing, documentation, and release packaging.

## [1.0.0-beta.2] - 2026-07-11

### Fixed

- Replaced the permissive line-split skill frontmatter check with PyYAML
  `safe_load`, duplicate-key detection, exact 12-skill inventory checks, and
  negative fixtures for invalid YAML types/tags.
- Converted all 12 skill descriptions to valid folded YAML scalars; eight were
  invalid under a strict YAML parser in `beta.1`.
- Added a safe, idempotent `init_workspace.py` that creates a standalone
  `main` history, never creates a remote, and formalizes `untracked`,
  `local-git`, and `private-approved` memory modes.
- Split immutable release validation (`runtime`) from mutable workspace
  validation (`operational`) and excluded virtual environments correctly.
- Replaced lifecycle tests that manually seeded Git with clean-ZIP onboarding,
  matter, branch, session, handoff, safety, and HTML/DOCX synthetic gates.

### Changed

- Added explicit project trust, `/hooks`, `/skills`, `/agent`, and rules
  verification instructions plus native PowerShell onboarding.
- Added a sanitized no-model Codex app-server/config/skills/hooks/rules probe;
  manual trust and model behavior remain separate gates.
- Made verifiable-document builds warning-strict by default and made absolute
  paths, unverified material evidence, and unverified page-image/OCR evidence
  blocking errors.
- Made `PACKAGE_MANIFEST.json` the canonical machine-readable version source
  and expanded Linux/macOS/Windows CI coverage.
- Added a deterministic SPDX 2.3 SBOM as a third release asset.
- Added GitHub artifact attestations for the release ZIP and SBOM as a
  compensating provenance control where a maintainer signing key is absent.
- Pinned runtime document/validation dependencies to the versions used by the
  beta.2 compatibility gates.
- Updated SHA-pinned GitHub Actions and added dependency review.

### Security

- `1.0.0-beta.1` is retained for reproducibility but marked superseded and
  unsuitable for legal work.

## [1.0.0-beta.1] - 2026-07-11

### Added

- First public beta of the independent `minius_codex_lab` project.
- Canonical legal-work skills and specialized roles.
- Sanitized runtime workspace template separated from the public upstream.
- Verifiable HTML/DOCX document builder and validator.
- Profile-based repository safety scanning and workspace validation.
- Deterministic, allowlisted Release ZIP and SHA-256 generation.
- Unit, lifecycle, distribution-safety, and reproducibility checks.
- Public CI, tag-driven pre-release workflow, contribution templates, security
  policy, governance, roadmap, and Apache-2.0 licensing.

### Changed from the internal seed

- Removed the private-repository bootstrap model and migrated to a public
  source repository with local/private runtime workspaces.
- Renamed public branding and release assets to `minius_codex_lab`.
- Replaced internal version `1.0.0` with the first public pre-release version
  `1.0.0-beta.1`.
- Added explicit non-affiliation, human legal-review, and public data-boundary
  requirements.

### Known limitations

- User workspaces are upgraded manually; no manifest-aware updater exists yet.
- Codex CLI hook/rule compatibility was not verified locally during migration.
- Beta contracts and layout may change before a stable release.
