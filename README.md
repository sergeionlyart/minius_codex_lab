# minius_codex_lab

Current version: **1.0.0-beta.1**

`minius_codex_lab` is an open-source source repository for Codex skills,
specialized roles, safety controls, and verifiable-document tooling used to
build a separate legal-work runtime workspace.

> **Independent project and legal-review notice:** this project is not an
> official product, system, service, or position of the Ministry of Justice of
> Ukraine, OpenAI, or any other government body or organization. It does not
> guarantee legal correctness and does not provide an official legal decision.
> Every legally significant output requires review and approval by a qualified,
> authorized human.

## Beta status

`1.0.0-beta.1` is the first public pre-release. Interfaces, workspace layout,
and upgrade procedures may still change. Existing user workspaces are upgraded
manually; there is no automatic updater yet.

## Choose the right installation

### End users: install the Release ZIP

Do not clone this source repository as a working legal matter. From the GitHub
Releases page, download:

- `minius_codex_lab-workspace-v1.0.0-beta.1.zip`
- `minius_codex_lab-workspace-v1.0.0-beta.1.zip.sha256`

Verify the checksum before extraction:

```bash
sha256sum -c minius_codex_lab-workspace-v1.0.0-beta.1.zip.sha256
```

On macOS:

```bash
shasum -a 256 -c minius_codex_lab-workspace-v1.0.0-beta.1.zip.sha256
```

On PowerShell, compare the printed hash with the first value in the
`.sha256` file:

```powershell
Get-FileHash .\minius_codex_lab-workspace-v1.0.0-beta.1.zip -Algorithm SHA256
```

Extract the ZIP into a new local or organization-approved private working
folder, not over an upstream checkout. Then run:

```bash
python3 scripts/check_repo_safety.py --profile workspace-local
```

Read the runtime `README.md`, `AGENTS.md`, and `SECURITY.md` before adding
documents. A private repository is not automatically an approved store for
personal, restricted, privileged, or otherwise protected information.

### Developers: clone the source

Clone the repository only to develop and review the distribution:

```bash
git clone https://github.com/sergeionlyart/minius_codex_lab.git
cd minius_codex_lab
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install "PyYAML>=6.0.2,<7" "ruff>=0.11,<1" "pytest>=8,<10"
python -m pip install -r tools/verifiable_document/requirements.txt
python3 scripts/validate_workspace.py --mode upstream
python3 scripts/check_repo_safety.py --profile upstream-public
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tools/verifiable_document/tests -v
```

The public repository owner and URL were verified before publication. See
`docs/DEVELOPMENT.md` for all gates.

## What is included

- canonical skills in `.agents/skills/`;
- specialized roles in `.codex/agents/`;
- a sanitized runtime template in `workspace-template/`;
- deterministic verifiable-document tooling in `tools/`;
- public-safety, validation, and reproducible release tooling in `scripts/`;
- tests, CI, security documentation, and open-source governance.

The release builder assembles an allowlisted workspace. The maintainer
`AGENTS.md`, GitHub metadata, tests, bootstrap inputs, Git history, caches,
real matters, session memory, logs, and generated artifacts are not release
payload.

## Security and privacy limits

The public upstream may contain code, templates, schemas, documentation, and
explicitly synthetic fixtures only. Never submit real:

- matters, party names, case numbers, source documents, or legal drafts;
- user/session memory, handoffs, raw or curated operational logs;
- generated reports, artifacts, exports, or research results;
- credentials, tokens, local configuration, personal data, or restricted data.

`.gitignore` is only a first line of defense. The staged/tracked-content
scanner is a required gate. See `SECURITY.md`,
`docs/PUBLIC_REPOSITORY_MODEL.md`, and `docs/THREAT_MODEL.md`.

## Compatibility

Python 3.11 is the documented runtime and configured CI target. A successful
remote CI run must still be verified before the first release. The local Codex
CLI and its support for project hooks/rules were not available for runtime
verification during the initial migration; compatibility claims are therefore
intentionally limited. See `docs/COMPATIBILITY.md`.

## Reporting and contributing

Use the issue forms for reproducible bugs, feature requests, and skill
proposals. Never include real legal or personal data in an issue. Report
security vulnerabilities privately as described in `SECURITY.md`.

Contributions are accepted under Apache License 2.0. By submitting a
contribution, you agree that it may be distributed under the project license.
See `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SUPPORT.md`.

## Documentation

- `ARCHITECTURE.md` — upstream/runtime boundary and build model.
- `docs/DEVELOPMENT.md` — setup and quality gates.
- `docs/RELEASING.md` — verified release process.
- `docs/PUBLIC_REPOSITORY_MODEL.md` — allowed and prohibited data.
- `docs/COMPATIBILITY.md` — supported and unverified environments.
- `docs/THREAT_MODEL.md` — security assumptions and residual risks.
- `docs/PROVENANCE.md` — origin and migration record.
- `GOVERNANCE.md` and `ROADMAP.md` — decision process and planned work.
