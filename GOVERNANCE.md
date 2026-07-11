# Governance

## Project model

`minius_codex_lab` begins with a maintainer-led governance model. Maintainers
are the accounts with verified repository administration/write authority; no
individual or organization is invented in this document.

The project is independent and is not governed by, or an official project of,
the Ministry of Justice of Ukraine, OpenAI, or another government body.

## Responsibilities

Maintainers:

- protect the public data and security boundary;
- review code, skills, roles, documentation, dependencies, and release assets;
- ensure quality gates and reproducibility pass;
- triage issues and security reports;
- document decisions and compatibility changes;
- apply the Code of Conduct fairly.

Contributors may propose and implement changes but do not gain authority to
publish releases, approve legal conclusions, or represent the project.

## Decision process

- Routine compatible fixes: pull request review and passing gates.
- New backward-compatible skills/features: linked issue, contract, tests, docs,
  and maintainer approval.
- Breaking contracts or major architecture/security changes: prior RFC/ADR,
  migration plan, and major-version assessment.
- Security-sensitive decisions: private review until disclosure is safe.
- Releases: follow `docs/RELEASING.md`; failed gates are vetoes.

Maintainers seek reasoned consensus. If consensus is not available, the
maintainer accountable for the affected component records the decision,
evidence, alternatives, and revisit condition. Repository-owner permissions are
the final operational authority for publication.

## Ownership

Every shared output has one explicit writer. Review and audit roles provide
findings rather than concurrently editing the final text. Repository ownership
was verified as `sergeionlyart/minius_codex_lab`; `.github/CODEOWNERS` routes
changes to `@sergeionlyart` without requiring external approval from a solo
maintainer.

## Versioning

The project uses Semantic Versioning:

- major — breaking workspace, skill, role, manifest, or updater contract;
- minor — backward-compatible skill or feature;
- patch — compatible correction;
- pre-release suffix — stability has not yet been established.

## Changes to governance

Governance changes require a public pull request explaining the reason,
security/privacy impact, and transition. The history of accepted changes
remains visible; it is not rewritten for convenience.
