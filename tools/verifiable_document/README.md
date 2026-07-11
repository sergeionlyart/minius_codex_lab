# Verifiable legal document tool

Локальный конвейер связывает каждый существенный тезис итогового юридического текста с точным предложением/абзацем источника в приложении того же файла.

## Что проверяется автоматически

- уникальность section/block/claim/source/unit IDs;
- наличие evidence у material claims;
- разрешение evidence/counterevidence refs на exact units;
- SHA-256 исходного файла и нормализованного текста каждого unit;
- обязательные locator и verification status;
- существование всех внутренних HTML anchors и DOCX bookmarks.

Автоматическая проверка не доказывает юридическую применимость, полноту поиска, правильность квалификации или достаточность фрагмента. Это предмет независимого юридического аудита.

## 1. Создание source object

```bash
python3 tools/verifiable_document/ingest.py \
  --input matters/2026-001/sources/act.txt \
  --output matters/2026-001/evidence/SRC-001.json \
  --source-id SRC-001 \
  --title "Название источника" \
  --authority "Орган" \
  --identifier "Реквизиты" \
  --type normative-act \
  --jurisdiction Ukraine \
  --version-date 2026-07-11 \
  --as-of 2026-07-11 \
  --retrieved-at 2026-07-11T12:00:00Z \
  --official-url "https://official.example/source" \
  --unit-mode paragraph \
  --verification-status needs-human-verification
```

Поддерживаются TXT/MD/HTML, DOCX через `python-docx` и text-based PDF через `pypdf`. Для скана инструмент прекращает работу: page-image evidence и OCR-фрагмент должны быть подготовлены отдельно и проверены человеком.

## 2. Создание document spec

Возьмите `examples/spec.example.json` как контракт структуры. Source object из предыдущего шага вставляется в массив `sources`. Основной текст строится из блоков:

- `paragraph` — контекст без самостоятельного существенного утверждения;
- `heading` — подзаголовок;
- `claim` — адресуемый тезис с `evidence_refs` и при необходимости `counterevidence_refs`.

## 3. Валидация и сборка

```bash
python3 tools/verifiable_document/validate.py \
  matters/2026-001/drafts/report.spec.json \
  --report matters/2026-001/reviews/report.validation.json

python3 tools/verifiable_document/build.py \
  matters/2026-001/drafts/report.spec.json \
  --out-dir matters/2026-001/outputs/verifiable \
  --html --docx
```

Для установки optional dependencies:

```bash
python3 -m pip install -r tools/verifiable_document/requirements.txt
```

## 4. Human review gate

До выдачи DOCX/PDF человек проверяет клики, bookmarks, оговорки источника, редакцию нормы, scope/time applicability, adverse authority, визуальное отображение и допустимость включения полного текста приложений. Validation/build reports сохраняются рядом с документом.

## Пример и тесты

```bash
python3 tools/verifiable_document/validate.py \
  tools/verifiable_document/examples/spec.example.json

python3 tools/verifiable_document/build.py \
  tools/verifiable_document/examples/spec.example.json \
  --out-dir .tmp/verifiable-example --html --docx

python3 -m unittest discover -s tools/verifiable_document/tests -v
```
