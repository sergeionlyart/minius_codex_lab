# Contributing

Thank you for improving `minius_codex_lab`. Contributions are reviewed as
changes to a public safety-sensitive distribution, not as a place to conduct a
real legal matter.

## Before contributing

- Read `CODE_OF_CONDUCT.md`, `SECURITY.md`, root `AGENTS.md`, and
  `docs/PUBLIC_REPOSITORY_MODEL.md`.
- Search existing issues before opening a new one.
- Use private vulnerability reporting for security defects.
- Never attach real case files, party details, client facts, operational logs,
  personal data, secrets, or restricted information.

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install "PyYAML>=6.0.2,<7" "ruff>=0.11,<1" "pytest>=8,<10"
python -m pip install -r tools/verifiable_document/requirements.txt
```

Run the complete gate set described in `docs/DEVELOPMENT.md`.

## Proposing a change

1. Open a focused issue using the appropriate form.
2. State the user problem and acceptance criterion.
3. For behavior changes, add a reproducing test or synthetic fixture first.
4. Make the smallest coherent change.
5. Update affected contracts, documentation, and `CHANGELOG.md`.
6. Run lint, tests, validation, safety, build, and reproducibility checks.
7. Open a pull request using the template and disclose any breaking change.

Large architecture, security-boundary, or compatibility changes should begin
as an RFC/ADR discussion before implementation.

## Skills and roles

A skill proposal must define job-to-be-done, typical user, trigger and
non-trigger conditions, inputs, outputs, evidence and privacy requirements,
failure/stop conditions, a reproducible synthetic task, acceptance criteria,
and compatibility impact.

A role must have one narrow responsibility, explicit allowed/prohibited
actions, read-only access by default for research/audit, a bounded write scope
when writing is necessary, and a structured handoff. Multiple roles must not
edit the same final document concurrently.

See `docs/SKILL_AND_ROLE_CONTRACTS.md`.

## Tests and fixtures

- Use artificial or fully anonymized fixtures only.
- Do not turn public court or government records into fixtures merely because
  they are publicly accessible; minimize and synthesize data where possible.
- A bug fix should fail before the fix and pass after it.
- Keep tests deterministic and independent of live legal sources.

## Pull-request expectations

Reviewers expect:

- a focused reason and linked issue;
- changed public contracts identified;
- tests and exact commands/results;
- safety/privacy review;
- documentation and changelog updates;
- no real legal/user data;
- an explicit compatibility and breaking-change assessment.

## Licensing

The project is licensed under Apache License 2.0. Unless you explicitly state
otherwise, an intentional contribution submitted for inclusion is provided
under that same license, as described in Section 5 of `LICENSE`.
