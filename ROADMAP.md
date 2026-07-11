# Roadmap

The roadmap is directional, not a delivery promise. Security, data separation,
tests, and reproducibility take priority over schedule.

## 1.0 beta hardening

- Gather sanitized compatibility results across supported environments.
- Expand safety-scanner and release lifecycle fixtures.
- Validate skill and role contracts against realistic synthetic tasks.
- Improve documentation from first-user feedback.
- Stabilize the workspace manifest before a `1.0.0` release.

## Planned milestones

1. **Manifest-aware workspace updater**

   Update unchanged managed files only; never overwrite user matters, memory,
   logs, or artifacts. Emit `.new` files and a conflict report.

2. **Reusable Codex plugin packaging**

   Evaluate packaging canonical skills and roles without weakening the
   standalone Release ZIP or public data boundary.

3. **Sanitized legal-workflow evaluation corpus**

   Build artificial, reproducible evaluation cases with no real party or user
   data.

4. **Ukrainian terminology and multilingual documentation audit**

   Review legal terminology, translations, and accessibility with qualified
   human reviewers.

5. **Expanded public-distribution threat model and contribution scanning**

   Cover more secret/PII patterns, malicious fixtures, binary formats, and
   dependency/supply-chain scenarios.

6. **Optional Obsidian-compatible local memory adapter**

   Design only after the core workspace contract stabilizes. It must remain
   local, optional, and unable to publish user memory by default.

The sixth item is explicitly post-bootstrap and is not implemented in
`1.0.0-beta.1`.
