# Public repository model

## Purpose

This repository publishes maintainable source and a sanitized workspace
distribution. It is not a place to perform or synchronize legal work.

## Allowed upstream content

- skills and role definitions;
- empty templates and schemas;
- deterministic tools and scripts;
- tests using artificial or fully anonymized fixtures;
- documentation, CI, governance, and release metadata.

Synthetic fixtures must be visibly labeled, minimal, and unrelated to a real
person or confidential matter.

## Prohibited upstream content

- real `matters/<matter-id>/` and source documents;
- legal drafts, research results, reports, exports, and generated artifacts;
- session memory, handoffs, model/tool logs, shell history, or local state;
- personal data, privileged/confidential information, investigation/sealed
  material, official-use information, state secrets, or other restricted data;
- tokens, keys, cookies, credentials, `.env`, or identity-bearing local paths;
- opaque input/release archives outside the controlled build output.

Public availability of a court decision or government record does not remove
the duty to minimize data or justify its inclusion as a fixture.

## Repository versus installed workspace

| Property | Public upstream | Installed workspace |
|---|---|---|
| Purpose | Develop and build | Perform local legal work |
| Matters | Template/synthetic only | User-controlled |
| Memory/logs/artifacts | Empty seeds only | Local, potentially sensitive |
| Remote | Exact public project repository | Optional and policy-controlled |
| Safety profile | `upstream-public` | `workspace-local` or `workspace-private` |

Users should install the Release ZIP in a separate folder. They should not
unpack it over a source checkout or submit their workspace back upstream.

## Defense in depth

1. `.gitignore` reduces accidental staging.
2. The scanner evaluates tracked/staged paths and content; ignore rules alone
   are never proof of safety.
3. The release builder starts from an allowlist rather than subtracting unsafe
   paths from a workspace.
4. The assembled ZIP is scanned, verified, extracted cleanly, and tested.
5. CI for untrusted pull requests has read-only permissions.
6. Human review confirms fixture provenance and semantic safety.

## Safety profiles

- `upstream-public`: blocks runtime/user data and requires the exact public
  repository identity when remote verification is requested.
- `workspace-local`: remote is optional; secrets, PII, and restricted markers
  remain blocking.
- `workspace-private`: may verify a private remote, but private visibility
  does not authorize restricted data.

## Contribution rule

When a bug can only be demonstrated with real data, first create a synthetic
minimal reproduction outside Git, verify it contains no identifying facts, and
then run the public profile before staging.
