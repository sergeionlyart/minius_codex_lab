# Threat model

## Scope

This model covers the public source repository, contribution workflow,
release-build pipeline, generated workspace ZIP, and the boundary to an
installed user workspace. It does not certify an organization's endpoint,
network, legal-data processing, or authorization controls.

## Assets

- integrity of skills, roles, hooks, rules, validators, and release tooling;
- confidentiality of contributor and end-user data;
- authenticity and reproducibility of release assets;
- traceability of verifiable-document evidence;
- project identity and non-affiliation;
- CI credentials and GitHub release authority.

## Trust boundaries

1. Public contributor input enters issues and pull requests.
2. Seed/runtime sources enter the allowlisted release builder.
3. CI code executes with a GitHub token.
4. A downloaded ZIP crosses into a user-controlled environment.
5. Legal documents and web content enter the installed workspace as untrusted
   data.
6. Model output crosses to a human legal decision.

## Threats and controls

| Threat | Principal controls | Residual risk |
|---|---|---|
| Real case/PII committed upstream | Ignore rules, profile scanner, synthetic-fixture policy, review | Novel identifiers or semantic PII may evade patterns |
| Secret or credential exposure | Filename/content patterns, minimal CI permissions, no printed secrets | Encoded or unknown credential formats |
| Prompt injection in documents/issues | Treat content as data; do not execute embedded instructions; bounded tools | Human or model may still misclassify an instruction |
| Malicious contributor changes hooks/rules/build | Review, tests, pinned actions, protected main, allowlisted build | Compromised maintainer account |
| Pull request obtains write token | Workflow-level `contents: read`; no write job on PR | Third-party service behavior outside repository control |
| ZIP path traversal, symlink, duplicate, special entry | Pre/post-build archive validation and clean extraction | Parser/platform discrepancies |
| Release artifact substitution | Exact-tag rebuild, SHA-256, manifest, reproducibility check | Compromised GitHub account/infrastructure |
| User workspace accidentally pushed upstream | Separate install directory, profiles, docs, path blockers | User bypasses controls or stages ignored tracked data |
| Private repo treated as authorization | Explicit policy and scanner profile semantics | Organization applies an unsafe local exception |
| Hallucinated/outdated legal conclusion | Source provenance, exact locators, version checks, independent audit, human approval | Tooling cannot prove legal correctness |
| Hidden DOCX/PDF metadata or broken visual output | Metadata checks, re-extraction, render/visual QA, human review | Format-specific hidden channels |
| Dependency/supply-chain compromise | Bounded dependencies, Dependabot, full-SHA actions, review | Upstream package or action-account compromise |

## Abuse cases

- A contributor disguises a real legal document as a fixture.
- An issue asks the agent to reveal a token or change `AGENTS.md`.
- A modified builder silently includes `.bootstrap/` or user matters.
- A tag workflow uploads a ZIP built before the tag.
- A runtime hook performs network or Git write operations.
- A technically valid evidence link is used to imply legal truth.

Tests and review should explicitly exercise these cases with synthetic inputs.

## Out of scope

- certification for classified or regulated processing;
- legal advice or correctness guarantees;
- endpoint malware, physical access, and organization IAM beyond documented
  integration boundaries;
- availability or authenticity guarantees for external legal websites;
- safe automatic upgrade of existing user workspaces in beta.1.

## Review triggers

Update this model when adding a dependency, networked service, plugin,
automatic updater, new binary format, write-capable role, release channel, or
data class. Security fixes should include a regression test and the control
change here.
