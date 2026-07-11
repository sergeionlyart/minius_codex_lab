# Codex smoke-test на синтетических данных

Этот gate подтверждает фактическую активацию project config, skills, roles,
hooks и rules. Он выполняется после `scripts/init_workspace.py`, но до загрузки
реальных материалов. Не включайте в transcript имена людей, номера дел,
закрытые факты, auth paths или токены.

## Предусловия

```bash
git status --short --branch
python scripts/validate_workspace.py --mode operational
python scripts/check_repo_safety.py --profile workspace-local
codex --version
```

Рабочее дерево должно быть чистым, а версия Codex — записана в результат.

## Project trust и hooks

1. Просмотрите `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/*.py` и
   `.codex/rules/default.rules`.
2. Запустите Codex из точного Git-корня и примите project trust через доступный
   интерфейс Codex.
3. Выполните `/hooks`. Ожидаются два project hooks без parse errors:
   `SessionStart` и `Stop`.
4. Доверьте только текущие определения hooks и начните новую сессию.
5. В начале новой сессии должен появиться прозрачный блок
   `[REPOSITORY OPERATIONAL MEMORY]`. Hook не должен менять файлы или Git.
6. Создайте только синтетическое незакоммиченное изменение и завершите turn.
   `Stop` должен предупредить о handoff; затем уберите изменение безопасным
   точечным способом.

Project trust и hook trust — разные проверки. Изменение определения hook
аннулирует ранее данное доверие к его hash.

## Skills

Выполните `/skills` и проверьте наличие всех project skills:

```text
case-law-analysis
eu-acquis-analysis
legal-drafting
legal-monitoring
legal-qa-audit
matter-intake
quantitative-impact-analysis
redaction-and-disclosure
session-memory-handoff
source-provenance
ukrainian-legal-research
verifiable-legal-document
```

Общее число может быть больше 12 из-за user/admin skills. На полностью
синтетической теме вызовите `$matter-intake`, `$legal-monitoring` и
`$verifiable-legal-document`. В ответе должны быть видны соответствующие
contract stages; никакой skill не должен выдумывать источники или выполнять
push.

## Roles

Через `/agent` попросите:

- `privacy_reviewer` проверить только синтетическую строку и вернуть результат
  в чат без записи;
- `legal_drafter` составить короткий синтетический абзац и вернуть его только в
  чат без изменения workspace.

Проверьте, что появились отдельные agent threads, роли не вышли за narrow
contract, а read-only reviewer не изменил Git status.

## Rules без выполнения команды

```bash
codex execpolicy check --pretty --rules .codex/rules/default.rules -- git push origin main
codex execpolicy check --pretty --rules .codex/rules/default.rules -- git push --force origin main
codex execpolicy check --pretty --rules .codex/rules/default.rules -- git reset --hard HEAD~1
codex execpolicy check --pretty --rules .codex/rules/default.rules -- curl https://example.invalid
```

Ожидается: `prompt`, `forbidden`, `forbidden`, `prompt`. Команды после `--` не
исполняются evaluator-ом.

## Запись результата

Сохраните только санитизированные поля:

```text
tested_at_utc:
release_version:
asset_sha256:
initial_commit:
os_version_arch:
python_version:
git_version:
codex_version:
project_trust: PASS|FAIL
skills_expected_12: PASS|FAIL
roles_privacy_and_drafter: PASS|FAIL
hooks_discovered_2: PASS|FAIL
hooks_trusted_and_executed: PASS|FAIL
rules_4_cases: PASS|FAIL
html_docx_synthetic: PASS|FAIL
residual_notes:
```

Если любой шаг не подтверждён фактически, запишите `FAIL` или `NOT VERIFIED`;
не заменяйте его статической проверкой файлов.
