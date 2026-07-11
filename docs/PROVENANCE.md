# Provenance

## Imported seed

| Field | Value |
|---|---|
| Import date (UTC) | 2026-07-11 |
| Original archive | `minjust_codex_legal_workspace_v1.0.0.zip` |
| Archive SHA-256 | `31f4b066808fda73813e1bce5773d700227f137a6a6ff40417496a88cbf5926b` |
| Internal package name | `minjust_codex_legal_workspace` |
| Internal package version | `1.0.0` |
| First public version | `minius_codex_lab 1.0.0-beta.1` |

The archive was treated as untrusted bootstrap input. Its central directory,
paths, entry types, duplicate names, size, package manifest, checksums, hooks,
rules, configuration, and executable scripts were reviewed before migration.
The original archive is not part of Git history or release assets.

## Principal migrations

- Replaced the cancelled private-repository bootstrap with a public upstream
  and separate local/private installed workspace model.
- Renamed public project identity and release assets to
  `minius_codex_lab`.
- Split the maintainer `AGENTS.md` from the runtime legal instruction.
- Moved runtime configuration, hooks, rules, empty matters, memory seeds, logs,
  artifacts, and user scripts under `workspace-template/`.
- Kept skills, roles, and deterministic tools as canonical public source.
- Removed seed bootstrap instructions and input integrity metadata from the
  public payload; new manifests/checksums are generated during release build.
- Added profile-based safety scanning, public data allowlisting, deterministic
  ZIP construction, clean-extraction checks, and reproducibility testing.
- Added Apache-2.0 licensing, public documentation, CI/release automation,
  governance, contribution policy, and explicit non-affiliation/legal-review
  notices.

## Naming exception

The old `minjust` name appears here only to identify the imported seed and may
appear in historical migration records. It is not current branding and does
not imply affiliation with the Ministry of Justice of Ukraine.

No copyright owner, legal entity, e-mail address, or security contact was
invented during migration. No personalized `NOTICE` file was created.
