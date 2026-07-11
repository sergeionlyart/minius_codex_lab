# Отчёт об устранении замечаний аудита minius_codex_lab

Дата: **2026-07-11**

Исходное заключение:
`docs/task/MINIUS_CODEX_LAB_AUDIT_REPORT_2026-07-11.md`.

## Логика и корневая причина

Главная ошибка была не в одном `SKILL.md`, а в несоответствии модели проверки
реальному контракту. Внутренний validator делил строки frontmatter по первому
двоеточию и тем самым проверял собственный упрощённый формат, тогда как Codex
skills документированы как YAML. Восемь некавыченных descriptions содержали
`: ` и не проходили строгий YAML parser, но ложноположительно проходили CI.

Тот же класс ошибки повторился в onboarding: lifecycle tests вручную делали
`git init`, `git add -f .` и initial commit, поэтому не тестировали путь
стороннего пользователя из чистого ZIP. Наличие `.codex/` файлов ошибочно
считалось доказательством project trust, hook trust и runtime activation.

## Выполненные исправления

| Замечание | Исправление | Проверяемый gate |
|---|---|---|
| P0-1, восемь invalid frontmatters | Все 12 descriptions переведены в folded YAML scalar | PyYAML `safe_load` всех 12 |
| P0-2, permissive validator | `safe_load`, duplicate/type/tag checks, exact 12-skill и 10-role inventories | positive/negative upstream и runtime tests |
| P0-3, Git отсутствует в happy path | Добавлен idempotent `init_workspace.py`; standalone `main`, manifest-only staging, no remote/push | clean-ZIP lifecycle tests |
| P0-4, нет trust onboarding | Разделены project trust и hook trust; добавлены `/hooks`, `/skills`, `/agent`, rules и synthetic checklist | `docs/CODEX_SMOKE_TEST.md` |
| P0-5, нет factual Codex smoke | Добавлен no-model app-server probe; отдельно выполнены три named skills и две roles в read-only ephemeral run | 12 probe checks PASS; Git unchanged |
| P1-1, memory/.gitignore contradiction | Формализованы `untracked`, `local-git`, `private-approved` | mode-aware init/lifecycle tests |
| P1-2, stale compatibility | Добавлен factual sanitized record и явные `NOT VERIFIED` human gates | `docs/COMPATIBILITY.md` |
| P1-3, POSIX-only onboarding | Добавлен native PowerShell сценарий без venv activation | Windows matrix lifecycle |
| P1-4, слабый golden E2E | Source ingest, semantic golden graph, HTML/DOCX anchors/bookmarks и обязательные negative fixtures | `run_synthetic_e2e.py` и tests |
| P2, supply chain/release | SHA-pinned Actions, dependency review, CodeQL, Dependabot alerts, exact deps, SPDX SBOM, artifact attestations | GitHub settings + release workflow |
| P2, duplicated version | `PACKAGE_MANIFEST.json` стал canonical source; Python constants и CI duplication удалены | `test_version_contract.py` |

Дополнительно `runtime` теперь означает неизменённый release integrity check,
а `operational` — проверку инициализированного изменяемого workspace. `.venv`
и `venv` исключены из integrity scan. Verifiable-document builder по умолчанию
блокирует warnings и отклоняет absolute paths, material claims без
human-verified evidence и непроверенный page-image/OCR evidence.

## Локальные доказательства

Выполняются следующие gates:

```bash
ruff check .
ruff format --check .
python3 scripts/validate_workspace.py --mode upstream
python3 scripts/check_repo_safety.py --profile upstream-public
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tools/verifiable_document/tests -v
python3 -m pytest
python3 scripts/build_release.py --check-reproducibility
```

Последний локальный deterministic build с manifest epoch до release commit:

```text
payload_files: 102
archive_sha256: 928f0d87f9aeb1242cfe004a7768017ec9397003675895a07859cd6ef522ad65
reproducibility: PASS
sbom: SPDX-2.3
```

Factual Codex metadata/config probe на чистом extracted candidate и
`codex-cli 0.144.0-alpha.4` прошёл 12/12 checks: project config layer,
`AGENTS.md`, 12 skills, 10 role TOMLs, два project hooks, idle no-turn
read-only/network-disabled thread, четыре execpolicy case и unchanged Git.

Отдельный synthetic model run фактически применил `$matter-intake`,
`$legal-monitoring`, `$verifiable-legal-document` и получил chat-only ответы от
`privacy_reviewer` и `legal_drafter`. Alpha CLI выдал thread-store warnings;
они сохранены как compatibility limitation, а не скрыты.

## Внешние меры

- GitHub Release `v1.0.0-beta.1` помечен
  `SUPERSEDED — DO NOT USE FOR LEGAL WORK`; тег и оба исходных asset сохранены.
- Secret scanning и push protection включены.
- Vulnerability alerts и Dependabot security updates включены.
- Dependency review выявил уязвимый historical pin `pypdf 5.0.0`; он заменён
  на актуальный `6.14.2`, поддерживающий Python 3.11, до merge.
- GitHub Actions требуют full-SHA pinning.
- CodeQL default setup для Python/Actions включён и прошёл initial scan.
- Публичный dependency graph формирует SBOM; новый release дополнительно
  публикует deterministic file-level SPDX 2.3 SBOM.

## Остаточные ручные gates

Эти проверки нельзя честно заменить CI и потому они переданы тестировщику:

- принять project trust только после просмотра `.codex/`;
- через `/hooks` проверить и доверить exact current hook definitions, затем
  подтвердить их фактическое выполнение;
- повторить `/skills` и role calls в своей версии Codex;
- визуально проверить DOCX и клики в Microsoft Word на Windows;
- проверить юридическую достаточность evidence человеком.

Отсутствует локальный GPG/SSH signing identity. Новый ключ не создавался и не
подменялся автоматически. Поэтому `beta.2` использует новый annotated tag,
release SHA-256, SPDX SBOM и GitHub artifact attestations; отсутствие
криптографической подписи maintainer tag явно указано в release notes.

## Публикационный статус

Push, merge и `v1.0.0-beta.2` разрешены только после полного local gate,
зелёных Linux/macOS/Windows checks на точном commit и повторной проверки
скачанных release assets. Ссылки на итоговый commit, CI и release добавляются
после их фактического появления; будущий результат не считается заранее
успешным.
