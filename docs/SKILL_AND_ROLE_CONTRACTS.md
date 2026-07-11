# Skill and role contracts

## Skill contract

Every `.agents/skills/<name>/SKILL.md` must provide:

1. YAML frontmatter with a unique directory-matching `name` and precise
   `description`.
2. Job-to-be-done.
3. Trigger and non-trigger conditions.
4. Required inputs and explicit outputs.
5. A step-by-step workflow.
6. Evidence, provenance, privacy, and safety requirements.
7. Failure modes and stop/escalation conditions.
8. Definition of done.
9. Automated fixtures/tests or a documented reproducible manual acceptance
   test.

Descriptions should route accurately without loading the entire skill. A skill
must not duplicate broad maintainer/runtime invariants.

## Role contract

Every `.codex/agents/*.toml` must define:

- `name`, `description`, and `developer_instructions`;
- one narrow responsibility;
- allowed and prohibited actions;
- `sandbox_mode = "read-only"` by default for research/audit;
- a minimal bounded write scope when writing is essential;
- required inputs and a structured handoff;
- failure/escalation behavior;
- prohibition on silently changing another role's conclusion.

A handoff reports status, evidence/artifacts with exact locators, limitations,
open questions, files changed (if any), and the owner/next action.

## Multi-role ownership

One coordinator assigns exactly one writer for each shared final document.
Researchers and auditors return evidence-ready notes/findings. A drafter owns
substantive text only when assigned. A document engineer may transform an
approved specification but may not alter the legal position.

## Change classification

- Repeated workflow → skill.
- Durable rule supported by recurring defects → `AGENTS.md`.
- Narrow specialization or independent check → role.
- Major cross-component choice → ADR/RFC.

Each behavioral correction begins with a reproducing test or fixture. Breaking
contracts require a major-version assessment; compatible new skills require a
minor-version assessment; compatible fixes require a patch-version assessment.
