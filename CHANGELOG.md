# Changelog

All notable public changes are documented here. The project follows Semantic
Versioning while pre-release compatibility remains explicitly limited.

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
