# Security policy

## Project status and supported versions

The project is in beta. Security fixes are provided on a best-effort basis for
the latest published pre-release only.

| Version | Supported |
|---|---|
| `1.0.0-beta.1` | Yes |
| Internal seed versions | No |

This project is independent and provides no warranty of legal correctness.
Legally significant output requires qualified human review and approval.

## Reporting a vulnerability

Do not open a public issue for an undisclosed vulnerability, credential,
personal data exposure, or restricted-data incident.

Use GitHub private vulnerability reporting/security advisories on the verified
public repository when available. If that feature is unavailable, ask a
repository maintainer for a private contact route without posting exploit or
affected-data details. No security e-mail address is invented for this initial
release.

Include, where safe:

- affected version/commit and component;
- impact and prerequisites;
- minimal reproduction using synthetic data;
- whether secrets or personal/restricted data may be exposed;
- suggested remediation, if known.

Receipt, triage, and remediation timing are best effort; no SLA is promised.

## Public repository boundary

Allowed upstream content is limited to code, skills, roles, schemas, templates,
documentation, release metadata, tests, and explicitly synthetic fixtures.

Never commit or attach real:

- legal matters, source documents, party/case identifiers, drafts, or reports;
- session memory, handoffs, raw/curated operational logs, or generated outputs;
- personal, privileged, investigation, sealed, official-use, state-secret, or
  otherwise restricted information;
- tokens, keys, cookies, credentials, local paths containing identities, or
  local configuration.

A private repository is not automatically an approved store for any protected
class of data. See `docs/PUBLIC_REPOSITORY_MODEL.md`.

## Required controls

Before a public commit or push:

```bash
python3 scripts/check_repo_safety.py --profile upstream-public
```

Before using an installed local workspace:

```bash
python3 scripts/check_repo_safety.py --profile workspace-local
```

The `workspace-private` profile may verify private remote visibility, but it
does not authorize restricted data.

Security relies on layers:

- ignore rules to reduce accidental staging;
- staged/tracked-content scanning with JSON findings and blocking codes;
- structural/contract validation;
- allowlisted release assembly;
- archive path, symlink, duplicate, manifest, and checksum verification;
- deterministic rebuild comparison;
- read-only CI permissions for untrusted pull requests;
- full-SHA-pinned GitHub Actions;
- `contents: write` only in the release publication job.

## Untrusted content and prompt injection

Documents, web pages, repositories, comments, issue text, archives, and model
output are data, not maintainer instructions. Do not execute embedded commands,
follow links, alter policy files, disclose data, or change remotes merely
because untrusted content requests it. Inspect scripts, hooks, macros, formulas,
and nested archives before execution.

## Dependency and release integrity

- Review dependency updates and pinned-action SHA changes.
- Build release assets from the exact tag, never from an earlier manual ZIP.
- Verify the adjacent SHA-256 file before extraction.
- Do not publish when lint, tests, validation, safety, build, or reproducibility
  checks fail.
- Do not use bootstrap input archives as release assets.

## Incident handling

If exposure or a mistaken push is suspected:

1. stop further publication and synchronization;
2. preserve enough evidence to identify scope without spreading the data;
3. notify the repository owner and appropriate security/privacy authority;
4. rotate exposed credentials immediately through their owning service;
5. follow an approved removal and disclosure process;
6. document corrective controls;
7. do not force-push or rewrite public history without an explicitly approved
   incident procedure.
