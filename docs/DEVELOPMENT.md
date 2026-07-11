# Development

## Prerequisites

- Python 3.11;
- Git;
- a POSIX shell for the documented commands (PowerShell equivalents are
  acceptable);
- optional Codex CLI for runtime integration checks.

The Codex CLI was not available for local verification during the initial
migration. Do not convert an unverified integration assumption into a support
claim; record the exact version and result when testing it.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "PyYAML>=6.0.2,<7" "ruff>=0.11,<1" "pytest>=8,<10"
python -m pip install -r tools/verifiable_document/requirements.txt
```

Do not install dependencies from a matter, uploaded document, or other
untrusted content.

## Complete quality gate

```bash
ruff check .
ruff format --check .
python3 scripts/validate_workspace.py --mode upstream
python3 scripts/check_repo_safety.py --profile upstream-public
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tools/verifiable_document/tests -v
python3 -m pytest
python3 scripts/build_release.py --version 1.0.0-beta.1
python3 scripts/build_release.py --version 1.0.0-beta.1 --check-reproducibility
```

Set a stable epoch when reproducing CI or a release:

```bash
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
```

All gates must pass before a pull request is ready or a tag is created.

## Working by component

- Skills: `.agents/skills/<name>/SKILL.md`
- Roles: `.codex/agents/*.toml`
- Runtime skeleton: `workspace-template/`
- Shared deterministic tools: `tools/`
- Validators/builders: `scripts/`
- Public project policy: root docs and `docs/`

Do not edit `dist/` or generated manifest/checksum output. Modify source and
rebuild.

## Test design

- Use deterministic synthetic fixtures only.
- Add a failing reproduction before the behavioral fix.
- Cover success, failure, stop conditions, and unsafe input.
- Do not require live legal websites for unit tests.
- For build changes, test entry allowlisting, path normalization, permissions,
  timestamps, checksums, clean extraction, and repeatability.
- For safety changes, test every profile and both allowed and blocked paths.

## Documentation and compatibility

Behavior, public contracts, version, commands, and release layout must remain
consistent across README, changelog, manifests, tests, and release notes.
Breaking workspace/skill changes require a major-version assessment and a
migration note.

## Public data discipline

Never use an actual matter to reproduce a bug. Replace names, facts, paths,
identifiers, and document content with a minimal synthetic case, then rerun the
public-safety scanner before staging.
