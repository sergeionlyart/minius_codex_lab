# ADR-0002: Web search mode

- **Status:** accepted
- **Date:** 2026-07-11

## Context

Юридическая работа требует актуальности, но live web retrieval повышает риск раскрытия запроса и prompt injection.

## Decision

Проектный default: `web_search = "indexed"`; shell network disabled. Для текущего законодательства пользователь запускает `codex --search` только после классификации и sanitization запроса. Research note всегда фиксирует дату получения и официальный первоисточник.

## Consequences

- Баланс актуальности и минимизации внешнего доступа.
- Для time-sensitive legal status может потребоваться отдельный live run.
- Restricted/personal facts не включаются в web query.
