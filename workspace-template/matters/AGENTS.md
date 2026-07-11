# AGENTS.md — правила для matters/

Корневой `AGENTS.md` действует полностью. Дополнительно:

- Одно дело — один каталог `matters/<matter-id>/`; не смешивай источники и evidence разных дел без явной cross-reference.
- До содержательной работы прочитай `MATTER.md` и `PLAN.md`. Не меняй scope молча.
- Исходные материалы не изменяй. Derived/extracted data храни отдельно и фиксируй provenance/hash.
- `sources/REGISTER.csv` и `evidence/CLAIMS.csv` являются критическими индексами. IDs стабильны; удаление записи заменяй status/notes, если на нее уже есть ссылки.
- Высокорисковые draft-файлы пишет один назначенный агент. Исследовательские субагенты возвращают отдельные notes/corpus rows.
- В `outputs/` помещай только воспроизводимые, проверенные версии с validation/audit report. Черновики остаются в `drafts/`.
- Restricted/personal files не храни в этом Git-дереве; используй утвержденное защищенное хранилище и безопасный reference в register.
- Перед handoff обнови session log и перечисли exact files/commit IDs.
