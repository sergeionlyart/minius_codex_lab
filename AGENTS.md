# Maintainer instructions

## Purpose

`minius_codex_lab` is the public source and distribution repository for an
independent legal-work workspace for Codex. It is not an official product,
system, or position of the Ministry of Justice of Ukraine, OpenAI, or any
government body. Never add real matters, client documents, operational memory,
logs, generated legal work, personal data, restricted information, or secrets
to this repository.

## Repository map

- `.agents/skills/` — canonical skill sources.
- `.codex/agents/` — canonical role sources.
- `workspace-template/` — runtime-only files and empty/seed data structures.
- `tools/` — deterministic document tooling.
- `scripts/` — validation, safety, and release tooling.
- `tests/` — unit, lifecycle, safety, and reproducibility tests.
- `docs/` — architecture, security, compatibility, development, and release policy.
- `dist/` — generated release artifacts; never commit it.

The root `AGENTS.md` governs maintainers. The runtime instruction shipped to
users is `workspace-template/AGENTS.md`; the release builder maps it to the
root of the generated workspace.

## Development commands

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install "PyYAML>=6.0.2,<7" ruff pytest
python -m pip install -r tools/verifiable_document/requirements.txt

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

## Change rules

- Keep skills canonical in `.agents/skills/`; every skill needs explicit
  trigger/non-trigger conditions, inputs, outputs, workflow, evidence and
  safety rules, stop conditions, definition of done, and a test fixture or
  documented acceptance test.
- Keep roles canonical in `.codex/agents/`; define a narrow responsibility,
  allowed and prohibited actions, write scope, and handoff format. Research
  and audit roles are read-only by default.
- Treat hooks, rules, configuration, manifests, and the release allowlist as
  security-sensitive. Review them before execution and test behavioral changes.
- Never edit generated ZIPs or checksums. Change source files and rebuild.
- A repeated procedure belongs in a skill; a durable cross-cutting rule belongs
  here; an independent specialization belongs in a role; a major architectural
  decision needs an ADR or RFC.
- Add a reproducing test or fixture before fixing a behavioral defect. Update
  documentation and `CHANGELOG.md` whenever behavior or a public contract changes.

## Pull-request readiness

A change is ready only when lint, formatting, unit tests, workspace validation,
the public-safety scan, release build, and reproducibility checks pass; affected
contracts and documentation are updated; and the diff contains no real legal or
user data.

## Versioning and releases

Use SemVer. Breaking workspace/skill contracts require a major version;
backward-compatible skills/features require a minor version; compatible fixes
require a patch. Use pre-release suffixes until stability is demonstrated.
Follow `docs/RELEASING.md`; never tag or publish when a quality gate fails.
