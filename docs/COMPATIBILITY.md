# Compatibility

## Support statement

Python **3.11** is the documented version and configured CI target for
`1.0.0-beta.1`. A successful remote CI run must be verified before release.
Other Python versions are unverified and may work, but are not support claims.

| Component | Status for beta.1 |
|---|---|
| Python 3.11 | Documented and configured in CI; first remote run pending |
| Linux GitHub runner | Configured; first remote run pending |
| macOS/Linux local shell | Expected; checksum commands documented |
| Windows/PowerShell | Runtime scripts included; full lifecycle not yet CI-tested |
| Codex CLI | Not verified locally during initial migration |
| Codex project hooks/rules | Configured in runtime template; compatibility unverified locally |
| HTML document output | Core path; standard-library build/validation |
| DOCX/PDF handling | Optional dependencies and mandatory human visual review |

## Codex compatibility

The runtime template uses project `AGENTS.md`, skills, specialized roles,
configuration, hooks, command rules, indexed web-search settings, and
multi-agent behavior. Exact support depends on the installed Codex version and
organization policy.

The project syntax was checked against the official
[configuration reference](https://developers.openai.com/codex/config-reference),
[hooks reference](https://developers.openai.com/codex/hooks),
[rules reference](https://developers.openai.com/codex/rules), and
[AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md) as of
2026-07-11. Project configuration is loaded only for trusted projects.

The local launcher returned `ENOENT`, so a factual Codex runtime smoke test
could not be completed. This release therefore does not claim a minimum Codex
build number. If a feature is unsupported:

- do not weaken safety policy;
- keep hooks disabled rather than emulating them unsafely;
- run validation/safety commands manually;
- report the exact `codex --version` and sanitized error;
- document verified results before changing this compatibility matrix.

## Python dependencies

Core safety, HTML generation, and release tooling target the Python standard
library where practical. YAML validation uses the bounded PyYAML dependency in
`workspace-template/requirements.txt`; optional document features use the
bounded dependencies in `tools/verifiable_document/requirements.txt`.

## Legal-source compatibility

Live legal websites and registries are external, changeable services. Their
availability is not an offline build requirement and is never assumed by unit
tests. A source must still be checked for authority, version, date, scope, and
exact support even when technically accessible.

## Reporting a compatibility result

Provide operating system, architecture, Python version, Codex version if
applicable, exact command, sanitized output, and whether optional dependencies
were installed. Never attach a real legal document.
