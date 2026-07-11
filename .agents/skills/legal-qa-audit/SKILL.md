---
name: legal-qa-audit
description: >-
  Проведи независимую юридическую и доказательственную проверку черновика:
  применимость норм, точность цитат, adverse authority, числа, overclaiming,
  ссылки, приватность и готовность. Используй перед выдачей; не используй как
  самоодобрение автора.
---

# Независимый legal/evidence audit

## Contract

- **Job-to-be-done:** независимо определить, готов ли материал, и выдать воспроизводимые findings без самоодобрения автора.
- **Inputs:** draft, scope, дата актуальности, evidence ledger, source register и validation reports.
- **Outputs:** findings с severity, claim/evidence IDs, шагом воспроизведения, минимальным исправлением и итоговым решением.
- **Evidence and safety:** работай read-only, проверяй adverse authority, privacy и exact locators; отсутствие доступа не означает pass.
- **Stop conditions:** останови решение о готовности, если отсутствует source/evidence set, версия документа или независимость reviewer.
- **Acceptance test:** вручную перепроверь один blocker и случайную выборку из пяти claims другим путем.

## Независимость

По возможности используй отдельного `evidence_auditor` и `privacy_reviewer`, которые не писали документ. Не исправляй silently; сначала создай findings.

## Проверочные треки

### A. Scope и статус

- вопрос, audience, jurisdiction, as-of date;
- draft/final/approved status;
- соответствие порученному product;
- явные assumptions и exclusions.

### B. Право

- существование и реквизиты акта;
- редакция/effective dates;
- hierarchy и scope;
- exact locator;
- exceptions/transitional rules;
- competence/procedure/remedy;
- adverse authority и unresolved conflict.

### C. Практика

- решение существует и официально доступно;
- holding не искажен;
- status/finality/instance;
- выборка и предел generalization;
- later/contrary treatment.

### D. Факты и данные

- source/chain of custody;
- число воспроизводимо;
- denominator, period, unit, method;
- sampling/comparability;
- no false precision;
- fact не смешан с inference.

### E. Claim-evidence alignment

Для каждого material claim спроси:

1. Источник содержит именно этот тезис?
2. Тезис не шире фрагмента?
3. Контекст/оговорка сохранены?
4. Источник относится к нужному времени/лицу/вопросу?
5. Есть ли counterevidence?
6. Достаточна ли authority/reliability?

### F. Документ

- internal/external links;
- cross-references и numbering;
- terms/definitions;
- contradictions/duplication;
- appendix completeness mode;
- source/unit hashes;
- metadata, tracked changes, comments, hidden text.

### G. Security

- classification;
- personal/restricted data;
- secrets/local paths;
- допустимость web/repo/publication;
- необходимая redaction.

## Severity

- `BLOCKER` — нельзя выдавать/публиковать;
- `MAJOR` — существенно меняет вывод/риск;
- `MINOR` — локальная неточность без изменения позиции;
- `OBSERVATION` — улучшение/неопределенность.

## Формат finding

```markdown
- ID: QA-001
- Severity: BLOCKER
- Claim/file/locator:
- Expected:
- Observed:
- Evidence/reproduction:
- Risk:
- Minimal remediation:
- Owner:
- Status:
```

## Решение о готовности

Возможные статусы:

- PASS — no blockers/majors, limitations disclosed;
- PASS WITH CONDITIONS — conditions перечислены и контролируемы;
- REVISE — major defects;
- BLOCK — unresolved blocker/security issue;
- NOT ASSESSABLE — недостаточно доступа/источников.

Не ставь PASS только потому, что автоматический validator завершился успешно.
