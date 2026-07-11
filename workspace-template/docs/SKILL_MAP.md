# Карта навыков

| Skill | Trigger | Основные outputs |
|---|---|---|
| `$matter-intake` | новое/неясное поручение | MATTER, PLAN, classification, evidence gate |
| `$source-provenance` | импорт/цитирование источника | register, hashes, locators, conflicts |
| `$ukrainian-legal-research` | действующее право Украины | applicable rule/version synthesis |
| `$case-law-analysis` | вывод о практике | protocol, corpus, holdings, limits |
| `$legal-monitoring` | полный L3 monitoring | passport, theory, causal/root-cause/recommendations |
| `$eu-acquis-analysis` | ЕС/ЕСПЧ/сравнение | legal status, gap/adaptation matrix |
| `$quantitative-impact-analysis` | статистика/impact | indicator dictionary, reproducible analysis |
| `$legal-drafting` | evidence gate пройден | memo/opinion/draft/report with claims |
| `$verifiable-legal-document` | высокий стандарт проверки | self-contained HTML/DOCX + report |
| `$legal-qa-audit` | перед выдачей | blocker/major/minor findings |
| `$session-memory-handoff` | параллельная/долгая работа | branch/worktree/session/CURRENT/commits |
| `$redaction-and-disclosure` | web/push/export | sanitized copy, disclosure decision/log |

## Типовые цепочки

### Быстрый ответ L0

`matter-intake (light) → ukrainian-legal-research → source-provenance → concise answer`

### Юридическая записка L1

`matter-intake → UA law + case law → source-provenance → legal-drafting → legal-qa-audit`

### Исследовательское досье L2

`matter-intake → parallel roles → evidence ledger/conflicts → options → audit → verifiable document`

### Мониторинг L3

`matter-intake → legal-monitoring orchestration → UA/practice/data/EU modules → causal/root cause → drafting → independent audit → verifiable document`
