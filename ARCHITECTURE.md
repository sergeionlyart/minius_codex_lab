# Architecture

## 1. System boundary

`minius_codex_lab` deliberately separates two products:

| Layer | Purpose | May contain user data? |
|---|---|---|
| Public upstream | Canonical source, tests, documentation, CI, release tooling | No |
| Release ZIP | Sanitized, ready-to-extract runtime workspace | Only empty templates and synthetic fixtures |
| Installed workspace | Local legal work controlled by the end user or organization | Potentially, under their policy; never synced upstream by default |

The upstream is not a legal case repository. A Release ZIP is generated from
reviewed sources; it is not a snapshot of an installed workspace.

## 2. Source layout

```text
.
├── AGENTS.md                 maintainer instructions
├── .agents/skills/           canonical skills
├── .codex/agents/            canonical roles
├── workspace-template/       sanitized runtime-only skeleton
├── tools/                    deterministic document tooling
├── scripts/                  validation, safety, and release tooling
├── tests/                    automated verification
├── docs/                     public project documentation
└── .github/                  CI, release, and contribution metadata
```

Runtime configuration, hooks, rules, empty matters/log/artifact structures, and
runtime `AGENTS.md` live under `workspace-template/`. Skills, roles, and
shared tools remain canonical at the upstream root and are mapped into the ZIP
by the release builder.

## 3. Release assembly

`scripts/build_release.py` uses an explicit allowlist. It:

1. maps `workspace-template/AGENTS.md` to ZIP-root `AGENTS.md`;
2. copies the sanitized runtime template;
3. adds canonical skills, roles, selected scripts, and document tooling;
4. generates a package manifest and checksums from the assembled payload;
5. normalizes entry order, timestamps, and permissions;
6. rejects path traversal, symlinks, duplicate entries, prohibited paths, and
   unsafe distribution content;
7. extracts into a temporary directory and runs lifecycle/safety verification;
8. verifies that two builds from the same commit and
   `SOURCE_DATE_EPOCH` have the same SHA-256.

The root maintainer `AGENTS.md`, `.github/`, `.git/`, `.bootstrap/`,
tests, caches, and `dist/` never enter the runtime ZIP.

## 4. Data and trust boundaries

Only code, templates, schemas, documentation, release metadata, and explicitly
synthetic fixtures are public-source inputs. Installed workspace paths such as
real `matters/<id>/`, operational memory, logs, artifacts, outputs, and source
documents are outside the public boundary.

Controls are layered:

- `.gitignore` reduces accidental staging;
- `check_repo_safety.py` scans staged/tracked content using a named profile;
- `validate_workspace.py` validates structure and contracts;
- the release builder starts from an allowlist and scans the assembled payload;
- CI runs all gates with a read-only token for pushes and pull requests;
- release publication receives `contents: write` only after quality gates pass.

No control makes a private repository an approved store for restricted data.

## 5. Skills, roles, and ownership

Skills hold repeatable workflows. Roles provide narrow, independently
reviewable specialization. Research and audit roles are read-only by default.
For shared outputs, the coordinator assigns exactly one writer; other roles
return evidence-ready handoffs and findings.

Behavioral contracts and change rules are documented in
`docs/SKILL_AND_ROLE_CONTRACTS.md`. Runtime legal methodology remains in the
runtime template and skills rather than expanding the maintainer instruction.

## 6. Verifiable documents

The document tool follows:

`source → addressable evidence unit → structured claim → validation → HTML/DOCX`

Stable IDs, source/unit hashes, internal links, backlinks, and validation
reports improve traceability. They do not prove that a source is legally
authoritative, current, applicable, or correctly interpreted. Human legal and
visual review remains mandatory.

## 7. Evolution

- Repeated procedures become skills.
- Durable cross-cutting maintainer norms belong in root `AGENTS.md`.
- Narrow independent work belongs in roles.
- Major architecture/security decisions require an ADR or RFC.
- Workspace or skill contract breaks require a major version.
- A manifest-aware updater may later update unchanged managed files, but it
  must never overwrite user matters, memory, logs, or artifacts.
