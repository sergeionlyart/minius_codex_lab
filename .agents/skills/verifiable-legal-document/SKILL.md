---
name: verifiable-legal-document
description: >-
  Собери проверяемый юридический документ: claim IDs, кликабельные внутренние
  ссылки на точные предложения/абзацы источников в приложениях, hashes и
  автоматический validation report. Используй для итогов высокой важности; не
  используй для неподтвержденного черновика.
---

# Проверяемый юридический документ

## Contract

- **Job-to-be-done:** собрать юридический документ, где существенные claims проверяются по внутренним ссылкам, evidence и hashes.
- **Inputs:** approved structured spec, evidence ledger, source fragments, output format и validation policy.
- **Outputs:** HTML/DOCX, evidence appendix, manifests/hashes и machine-readable validation report.
- **Evidence and safety:** не добавляй содержание вне ledger; минимизируй source fragments и проверяй metadata перед распространением.
- **Stop conditions:** останови build/release при missing evidence, broken anchors, hash mismatch, unsafe path или blocker validation.
- **Acceptance test:** вручную открой три claim links/backlinks, сверь fragments с источником и повтори validator.

## Цель

Сделать проверку тезиса быстрой и локальной: из основного текста пользователь кликает ссылку и попадает в том же HTML/DOCX на точное предложение/абзац приложения, подтверждающее тезис. Приложение хранит provenance, context, version и hash.

## Канонический pipeline

`источники → адресуемые evidence units → structured spec JSON → validator → self-contained HTML/DOCX → independent audit`

Подробная спецификация: `references/document-contract.md` и `docs/VERIFIABLE_DOCUMENT_SPEC.md`.

## Evidence model

- `claim_id` — уникальный тезис в основном документе.
- `claim_type` — fact/legal_proposition/numeric/quotation/interpretation/assumption/recommendation.
- `source_id` — конкретный источник/редакция.
- `unit_id` — точное адресуемое предложение или абзац.
- `evidence_refs` — список `unit_id`, поддерживающих claim.
- `counterevidence_refs` — фрагменты, ограничивающие/опровергающие claim.
- source SHA-256 и unit SHA-256 защищают от незаметной подмены.

## Режим приложения

1. **full** — полный нормализованный текст источника разбит на units. Предпочтителен для нормативных актов/судебных решений, если объем, право на воспроизведение и политика позволяют.
2. **evidence-pack** — точные cited units с достаточным контекстом, metadata, hash и ссылкой/путем к целому источнику. Используй, если полный документ нельзя законно/технически включить.
3. **page-image evidence** — для скана: релевантная страница/область + OCR/extracted text + marker `human-verified` или `needs-human-verification`.

Никогда не заявляй, что приложение полное, если включены только excerpts.

## Процедура

1. Убедись, что evidence gate пройден и source register завершен.
2. Для каждого разрешенного источника создай source object. Можно начать с:

```bash
python3 tools/verifiable_document/ingest.py \
  --input <source-file> \
  --source-id SRC-001 \
  --title "<title>" \
  --authority "<body/author>" \
  --retrieved-at 2026-07-11T00:00:00Z \
  --output <source-object.json>
```

Для machine-extracted PDF/DOCX проверь critical units вручную и обнови `verification_status`.
3. Создай spec по `tools/verifiable_document/examples/spec.example.json`.
4. Свяжи каждый material claim с точными `unit_id`. Ссылка не должна вести только на титульную страницу или весь документ.
5. Добавь counterevidence и qualifications там, где источник содержит оговорки.
6. Проверь spec:

```bash
python3 tools/verifiable_document/validate.py <spec.json> --report <validation.json>
```

7. Собери документ:

```bash
python3 tools/verifiable_document/build.py <spec.json> --out-dir <output-dir> --html --docx
```

`HTML` является каноническим self-contained форматом. `DOCX` создается при наличии `python-docx` и содержит internal hyperlinks/bookmarks.
8. Повтори validation после сборки. Не выдавай документ при blocker errors.
9. Для DOCX выполни visual QA: ссылки/bookmarks, переносы, таблицы, приложения, скрытые метаданные. Если renderer недоступен, явно передай этот пункт человеку.
10. Запусти независимый `$legal-qa-audit`.

## Обязательные проверки

- все material claims имеют evidence;
- все evidence refs разрешаются;
- нет duplicate IDs;
- file hash совпадает с записанным;
- unit hash совпадает с текстом;
- locator и verification status заполнены;
- ссылки ведут на exact unit и есть backlink;
- приложение раскрывает inclusion mode;
- unsupported/assumption claims визуально отличимы;
- adverse/counterevidence не скрыто;
- source metadata и retrieval date видимы;
- нет локальных секретных путей в публикуемом файле.

## Ограничение

Техническая валидность ссылок не доказывает правильность юридической интерпретации. Она доказывает только воспроизводимую связь между текстом тезиса и указанным фрагментом. Содержательная проверка остается обязательной.

## Definition of done

Validator завершился без errors, reviewer кликом проходит от каждого material claim к точному supporting unit, источник/версия/hash доступны, а validation report и audit findings сохранены рядом с документом.
