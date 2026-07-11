# ADR-0003: Verifiable document format

- **Status:** accepted
- **Date:** 2026-07-11

## Context

Пользователь должен переходить из тезиса итогового документа к точному предложению/абзацу источника в том же файле.

## Decision

Хранить содержание в structured JSON с `claim_id`, `source_id`, `unit_id`, hashes и locators. Канонический output — self-contained HTML с internal anchors; опциональный DOCX использует bookmarks/internal hyperlinks. Приложение содержит полный источник или явно обозначенный evidence pack.

## Consequences

- Ссылки и hashes можно валидировать детерминированно.
- Юридическая интерпретация все равно требует human audit.
- Для сканов нужен human verification evidence units.
