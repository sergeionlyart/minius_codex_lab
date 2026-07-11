# Compatibility

## Support statement

Python **3.11** is the documented runtime for `1.0.0-beta.2`. A row is a
support claim only when it records a factual run on the release commit or
asset. File presence and static parsing do not prove Codex activation.

| Component | beta.2 status |
|---|---|
| Python 3.11 | Local gates available; release-commit CI evidence is required before publication |
| Ubuntu 24.04 | Matrix configured; release-commit result pending |
| macOS 15 runner | Matrix configured; release-commit result pending |
| Windows 2025 runner | Matrix configured; release-commit result pending |
| HTML output | Synthetic links, anchors and hashes pass locally |
| DOCX output | Synthetic bookmarks and links pass technically; Microsoft Word visual QA not verified |
| Codex CLI | Local candidate smoke recorded below |
| Persisted project/hook trust in a user UI | **NOT VERIFIED**; mandatory third-party step |

The earlier Ubuntu run for `beta.1` proved only its then-current CI. It does not
establish `beta.2` compatibility because the old validator did not parse skill
frontmatter as strict YAML.

## Local Codex candidate record

Sanitized factual run on 2026-07-11:

| Field | Result |
|---|---|
| OS | macOS 26.3.1 (25D2128), arm64 |
| Python / Git | Python 3.12.0 for this smoke; Git 2.44.0 |
| Codex | `codex-cli 0.144.0-alpha.4` bundled with the desktop app |
| Workspace | Clean extracted `1.0.0-beta.2` candidate, initialized `local-git`, no remote |
| Project instructions | Runtime `AGENTS.md` loaded |
| Skills discovery | All 12 project skills loaded with normalized descriptions |
| Hooks discovery | Exact project `SessionStart` and `Stop` definitions discovered without parse errors; trust/execution not inferred |
| Skill execution | `$matter-intake`, `$legal-monitoring`, `$verifiable-legal-document` returned contract artifacts |
| Role execution | `privacy_reviewer` and `legal_drafter` returned synthetic chat-only results; parent thread-store warnings were emitted |
| Git after model run | Clean; read-only/ephemeral run made no workspace changes |
| Rules | push=`prompt`; force-push=`forbidden`; hard reset=`forbidden`; curl=`prompt` |
| HTML/DOCX | PASS through `scripts/run_synthetic_e2e.py` |

The automated run used `--ignore-user-config`, strict project config,
read-only sandbox, ephemeral state, and the documented automation-only hook
trust bypass after local hook review. That demonstrates parsing and execution
in this CLI build; it does **not** substitute for a third-party user accepting
project trust and exact hook trust through their Codex UI. The role run
completed, but the recorded thread-store warnings remain a compatibility note
for this alpha CLI.

The repeatable no-model metadata/config/rules probe also passed all 12 checks:

```bash
python3 scripts/codex_runtime_probe.py \
  --codex /Applications/ChatGPT.app/Contents/Resources/codex \
  --root /path/to/initialized/extracted-workspace
```

It uses an isolated temporary `CODEX_HOME`, starts no model turn, performs no
network transfer, does not execute evaluated commands, and requires unchanged
Git status. App-server currently exposes no project-role list endpoint, so the
10 role TOMLs are checked statically while runtime loading of the project
multi-agent config layer is verified separately.

## Required third-party Codex record

Follow the extracted `docs/CODEX_SMOKE_TEST.md` and report:

```text
tested_at_utc, release_tag, asset_sha256, initial_commit,
os_version_arch, python_version, git_version, codex_version,
project_trust, skills_expected_12, roles_privacy_and_drafter,
hooks_discovered_2, hooks_trusted_and_executed, rules_4_cases,
html_docx_synthetic, result, residual_notes
```

Do not include transcripts, auth paths, real legal documents, user identities,
tokens or restricted data.

## Codex compatibility boundaries

The runtime uses project `AGENTS.md`, `.agents/skills`, `.codex/agents`, project
config, hooks, command rules, indexed web-search defaults and multi-agent
behavior. Project config loads only for a trusted project; project trust and
hook-definition trust are separate gates. Exact behavior also depends on the
installed Codex version and organization policy.

The project syntax and onboarding are aligned with the official
[configuration reference](https://developers.openai.com/codex/config-reference),
[hooks reference](https://developers.openai.com/codex/hooks),
[skills reference](https://developers.openai.com/codex/skills),
[subagents reference](https://developers.openai.com/codex/subagents),
[rules reference](https://developers.openai.com/codex/rules), and
[AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md) checked
on 2026-07-11.

If a feature is unsupported, do not weaken safety policy. Keep the feature
disabled, run validation/safety commands manually, record the exact version and
sanitized diagnostic, and update this matrix only after a factual retest.

## Legal-source compatibility

Live legal websites and registries are external, changeable services. Their
availability is not an offline build requirement. Every source still requires
authority, version, date, scope and exact-support review even when technically
accessible.
