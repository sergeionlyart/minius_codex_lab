# Git как операционная память

## 0. Инициализация и режим хранения

Чистый release workspace сначала проверяется как неизменённый payload, затем
инициализируется только штатным скриптом:

```bash
python scripts/validate_workspace.py --mode runtime
python scripts/init_workspace.py --memory-mode untracked
```

`runtime` — integrity gate только до начала работы. После первого commit
используйте `--mode operational`.

Режим `untracked` не помещает реальные matters и mutable memory в Git.
`local-git` разрешает их явный локальный stage/commit. `private-approved`
требует отдельного организационного решения и флага
`--acknowledge-private-approved`; remote всё равно не создаётся автоматически.
Режим нельзя неявно менять повторным запуском initializer.

## 1. Ветки и worktrees

- `main` — reviewed durable state.
- `session/YYYYMMDD-<slug>` — одна исследовательская сессия/поток.
- Для нескольких параллельных чатов создавай отдельные worktrees, чтобы они не редактировали одни и те же файлы.
- Worktree с matter доступен только в tracked-режиме после явного commit этого
  matter. В `untracked` используйте branch в текущем рабочем каталоге.

Пример:

```bash
git worktree add ../project-wt-ua-law -b session/20260711-ua-law main
git worktree add ../project-wt-case-law -b session/20260711-case-law main
```

Slug нейтрален и не содержит фамилий/тайны.

## 2. Ownership

Перед параллельной работой coordinator распределяет files/directories. Один общий draft — один writer. Исследовательские роли пишут отдельные notes/corpora либо возвращают read-only results.

## 3. Смысловые коммиты

| Prefix | Содержание |
|---|---|
| `ops:` | конфигурация, scripts, hooks, templates |
| `matter:` | scope, intake, plan |
| `source:` | source register, versions, permitted snapshots |
| `research:` | analysis notes, corpus, data code |
| `evidence:` | claim-evidence/counterevidence, provenance |
| `draft:` | связный draft milestone |
| `review:` | findings, fixes, approvals |
| `decision:` | accepted ADR/policy decision |
| `memory:` | CURRENT/session handoff |
| `artifact:` | reproducible validated output |

Примеры:

```text
source: record applicable versions of enforcement procedure acts
evidence: link claims CLM-014–CLM-021 to verified court paragraphs
review: resolve major citation and denominator findings
memory: hand off case-law session with unresolved sample limitation
```

## 4. Когда коммитить

После завершенного проверяемого этапа: approved scope, source inventory, corpus freeze, evidence gate, coherent draft, audit pass, handoff. Не коммить после каждой команды и не оставляй огромный несвязанный diff.

## 5. Handoff

Создайте Python 3.11 virtual environment и установите ограниченную
runtime-зависимость командой `python -m pip install -r requirements.txt`.

Перед завершением:

```bash
git status --short --branch
git diff --check
python3 scripts/validate_workspace.py --mode operational
python3 scripts/check_repo_safety.py --profile workspace-local
```

Обнови session note и при необходимости CURRENT. В tracked-режиме stage только
названные пути после classification review. Покажи commit IDs и unresolved
risks. Скрипты lifecycle не выполняют commit или push.

## 6. Remote

- Внешний `origin` не обязателен; его добавляют только после явного решения о допустимых данных и модели доступа.
- Не заменяй существующий remote.
- Перед push: classification, staged file list, secret/sensitive scan, remote visibility.
- Обычный push требует approval; force-push запрещен.
- Даже private remote не подходит для `RESTRICTED` и по умолчанию для `PERSONAL`.

## 7. Merge

Coordinator/reviewer:

1. сравнивает branch with main;
2. проверяет source/evidence IDs и semantic conflicts;
3. запускает tests/audit;
4. merge только после approval;
5. обновляет CURRENT/decisions;
6. удаляет worktree/branch только после подтверждения сохранности истории.
