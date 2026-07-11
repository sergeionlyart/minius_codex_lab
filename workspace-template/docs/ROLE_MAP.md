# Карта ролей субагентов

| Role | Доступ | Когда использовать | Типовой выход |
|---|---|---|---|
| `legal_coordinator` | workspace-write | сложная L2/L3 задача, оркестрация | plan, delegation, integrated result |
| `ua_law_researcher` | read-only | редакции/применимость права Украины | rule synthesis + exact authorities |
| `case_law_analyst` | read-only | судебная/административная практика | protocol, corpus rows, synthesis |
| `eu_law_analyst` | read-only | EU/ECHR/international/comparative | status/gap/adaptation matrix |
| `policy_impact_analyst` | read-only | theory of change, causality, root cause | causal matrices/recommendations logic |
| `quantitative_analyst` | workspace-write | datasets/indicators/causal stats | code, tables, data-quality report |
| `legal_drafter` | workspace-write; no web | итоговый текст из evidence ledger | structured draft with claim IDs |
| `evidence_auditor` | read-only; no web | независимая проверка | severity findings / readiness status |
| `document_engineer` | workspace-write; no web | HTML/DOCX/anchors/hashes | document + validation report |
| `privacy_reviewer` | read-only; no web | перед web/remote/export | disclosure/redaction findings |

## Паттерн для L2/L3

1. Coordinator выполняет intake и делит вопрос.
2. Параллельно: UA law, case law, EU, data/policy — только независимые work packages.
3. Coordinator нормализует source/evidence IDs и принимает/отклоняет conflicts.
4. Drafter пишет один общий draft без web search.
5. Evidence auditor и privacy reviewer независимо проверяют.
6. Document engineer собирает проверяемый output.

## Антипаттерны

- Несколько субагентов одновременно редактируют один draft.
- Drafter сам ищет источники и сам себя аудирует.
- Research agent возвращает длинный пересказ без locators.
- Coordinator копирует сырые tool logs в main context.
- Subagent получает restricted facts для внешнего поиска.
