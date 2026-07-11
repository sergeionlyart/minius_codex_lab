---
name: session-memory-handoff
description: Начни, веди и заверши исследовательскую сессию с Git-операционной памятью: branch/worktree, session note, смысловые commits, CURRENT.md и handoff. Используй для параллельных/долгих задач; не используй для одношаговой задачи без durable state и не делай автоматический push.
---

# Межсессионная память и handoff

## Contract

- **Job-to-be-done:** сохранить минимальное устойчивое состояние и передать работу без сырых логов и скрытых решений.
- **Inputs:** session objective, branch/worktree, выполненные изменения, tests, риски и next action.
- **Outputs:** session log, обновленный CURRENT/index при необходимости и короткий handoff.
- **Evidence and safety:** не записывай секреты, raw prompts/tool logs и лишние персональные данные; сверяй memory с Git.
- **Stop conditions:** остановись, если session ID/path неоднозначен, есть конфликт владельцев или handoff раскроет restricted data.
- **Acceptance test:** новый reviewer вручную восстанавливает branch, scope, проверки, blockers и следующий шаг только из handoff.

## Принцип

Git хранит воспроизводимое состояние, `memory/` — краткую смысловую карту. Chat transcript не является источником истины.

## Начало сессии

1. Из корня прочитай `memory/CURRENT.md`, `OPEN_QUESTIONS.md` и active matter.
2. Убедись, что нет незавершенного конфликтующего владельца файлов.
3. Создай session note и ветку:

```bash
python3 scripts/start_session.py --slug <short-slug> --matter <matter-id> --create-branch
```

Для параллельной работы предпочтительно:

```bash
git worktree add ../<project>-wt-<slug> -b session/YYYYMMDD-<slug> main
```

Не включай confidential facts в slug/path.
4. В session note зафиксируй objective, inputs, files owned, planned skills/roles и evidence gate.

## Во время работы

Коммить завершенные смысловые этапы:

- `matter:` scope/plan;
- `source:` source register/import/version;
- `research:` analysis/corpus/data code;
- `evidence:` claim-evidence mapping;
- `draft:` coherent draft milestone;
- `review:` audit findings/fixes;
- `decision:` durable accepted decision;
- `memory:` session/CURRENT handoff;
- `artifact:` reproducible generated output;
- `ops:` configuration/tooling.

Commit message должен отвечать «какой устойчивый результат появился». Не смешивай unrelated changes. Не коммить пустой checkpoint ради ритуала.

## Что идет в CURRENT.md

Только устойчивое и короткое:

- active matters и цель;
- текущая accepted position/decision с ссылкой на файл/commit;
- last verified legal/data date;
- unresolved blockers/risks;
- active branches/worktrees;
- next actions и владельцы.

Не помещай туда сырые цитаты, длинные логи, secret values и весь ход рассуждения.

## Завершение

1. Обнови session note: work performed, artifacts, evidence added, decisions proposed/accepted, tests, unresolved items, next step.
2. Обнови `CURRENT.md`, только если durable state изменилось.
3. Выполни:

```bash
git status --short --branch
git diff --check
python3 scripts/validate_workspace.py
```

4. Создай локальный `memory:` commit, если есть handoff changes.
5. Покажи пользователю branch, commit IDs, changed files, tests, risks и ready-to-merge status.
6. Не push/merge без явного разрешения и security check.

## Конфликты параллельных сессий

- Один файл — один writer.
- Источники/evidence добавляй append-only по уникальным IDs, когда возможно.
- Не resolve semantic conflict автоматически. Создай `CONFLICTS.csv`/decision record и передай coordinator.
- Merge в main выполняй после evidence audit и review diff.

## Definition of done

Новая сессия может продолжить работу, прочитав repository files, без зависимости от предыдущего chat; Git history показывает смысловые этапы, а незавершенные вопросы не потеряны.
