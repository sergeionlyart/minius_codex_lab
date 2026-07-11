# Этап 2 — варианты внешней межсессионной памяти (не установлен)

Этот пакет сознательно ограничен этапом 1. Возможная следующая итерация:

## Наиболее простой вариант: Obsidian поверх `memory/` и `matters/`

- Открыть repository root как vault либо создать view-only vault с symlinks.
- Использовать backlinks/tags для matters, sources, claims и decisions.
- Не хранить отдельную копию истины: Markdown/CSV в Git остаются canonical.
- Не подключать community plugins без security review.

## Поиск и машинная память

- SQLite FTS для локального полнотекстового индекса;
- локальный vector index только над разрешенными материалами;
- внутренний MCP server с read-only search и policy-aware access;
- content hashes для incremental indexing;
- separate indexes по data class/matter.

## Критерии перехода

Этап 2 оправдан, когда linear search/Git перестают справляться: сотни дел, тысячи источников, повторное использование precedents и согласованная организационная инфраструктура. До этого простая файловая память надежнее и легче аудируется.
