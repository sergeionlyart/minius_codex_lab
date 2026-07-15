# Установка в Windows PowerShell

Требуются 64-bit Python 3.11+, Git for Windows и Codex. Распакуйте release ZIP
в новый автономный каталог вне другого Git repository.

## Проверка архива

```powershell
$Zip = ".\minius_codex_lab-workspace-v1.1.0-beta.1.zip"
$Expected = (Get-Content "$Zip.sha256").Split()[0].ToLowerInvariant()
$Actual = (Get-FileHash $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw "SHA-256 mismatch" }
```

После распаковки перейдите в корень workspace:

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r .\requirements.txt
& .\.venv\Scripts\python.exe .\scripts\validate_workspace.py --mode runtime
& .\.venv\Scripts\python.exe .\scripts\check_repo_safety.py --profile workspace-local
& .\.venv\Scripts\python.exe .\scripts\init_workspace.py --memory-mode untracked
```

Если Git identity отсутствует:

```powershell
& .\.venv\Scripts\python.exe .\scripts\init_workspace.py `
  --memory-mode untracked `
  --git-name "Your Name" `
  --git-email "you@example.org"
```

Initializer не создаёт remote и не делает push. После него:

```powershell
git status --short --branch
& .\.venv\Scripts\python.exe .\scripts\validate_workspace.py --mode operational
```

Проверьте `.codex\` и выполните ручной gate из
`docs\CODEX_SMOKE_TEST.md`. Project trust и hook trust нельзя считать
успешными только потому, что файлы присутствуют на диске.

## Синтетический lifecycle

```powershell
& .\.venv\Scripts\python.exe .\scripts\new_matter.py `
  --id synthetic-001 `
  --title "Synthetic legal question" `
  --classification PUBLIC
& .\.venv\Scripts\python.exe .\scripts\start_session.py `
  --slug first-review `
  --matter synthetic-001 `
  --create-branch
& .\.venv\Scripts\python.exe .\scripts\run_synthetic_e2e.py
& .\.venv\Scripts\python.exe .\scripts\validate_workspace.py --mode operational
& .\.venv\Scripts\python.exe .\scripts\check_repo_safety.py --profile workspace-local
```

Windows CI подтверждает Python/Git lifecycle и генерацию HTML/DOCX. Визуальная
проверка DOCX в Microsoft Word и интерактивные Codex trust steps остаются
отдельными человеческими проверками.
