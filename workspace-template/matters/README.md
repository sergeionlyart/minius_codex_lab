# Дела и исследования

Создавайте дело через:

```bash
python3 scripts/new_matter.py --id 2026-001 --title "Название" --classification INTERNAL
```

## Структура

- `MATTER.md` — scope, даты, audience, classification, assumptions.
- `PLAN.md` — вопросы, этапы, evidence gate, роли, review gates.
- `sources/` — реестр и разрешенные source snapshots.
- `evidence/` — claim ledger, missing data, conflicts.
- `research/` — notes, corpus, scripts, matrices.
- `data/` — разрешенные исходные/derived datasets и data dictionary.
- `drafts/` — рабочие документы.
- `reviews/` — audit findings и approvals.
- `outputs/` — проверенные итоговые артефакты и validation reports.

Имена matter IDs должны быть нейтральными и не раскрывать персональные/ограниченные сведения.
