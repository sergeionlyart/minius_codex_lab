# Спецификация проверяемого юридического документа

## 1. Пользовательский сценарий

Читатель видит тезис в основном документе, нажимает ссылку вида `[SRC-003, п. 47]` и попадает в том же файле на точное предложение/абзац приложения. Там видны текст, контекст, locator, source metadata, version, hash и обратная ссылка к тезису.

## 2. Два уровня проверки

### Техническая

- ссылочный target существует;
- IDs уникальны;
- source/unit hashes совпадают;
- material claim имеет evidence;
- appendix mode честно обозначен;
- internal hyperlinks/bookmarks разрешаются.

### Содержательная

- фрагмент действительно подтверждает тезис;
- тезис не шире источника;
- применима нужная редакция/time/scope;
- оговорки и counterevidence учтены;
- юридическая интерпретация обоснована.

Автоматический validator покрывает первое и часть второго; независимый юрист — второе.

## 3. Source appendix

### Full mode

Полный нормализованный source text включен в приложение и разбит на addressable units. Для official acts/judgments это preferred при допустимом объеме и праве на воспроизведение.

### Evidence-pack mode

Включены cited units с контекстом и immutable reference/hash целого источника. Используется для больших, лицензируемых, защищенных или технически сложных документов. Заголовок приложения явно говорит, что это extracts, а не полный текст.

### Scan mode

Для скана сохраняется page/region evidence, OCR text и verification status. Не маркируй machine OCR как human-verified.

## 4. Claim policy

Evidence обязателен для:

- fact;
- legal proposition;
- number/statistic;
- quotation.

Interpretation должна ссылаться на supporting units и быть видимо отделена от факта. Assumption допускается без evidence только с маркировкой, проверяемым планом и описанием влияния. Recommendation ссылается на доказанную проблему/root cause.

## 5. Форматы

- **HTML** — канонический self-contained output: надежные anchors, простой machine validation, печать в PDF.
- **DOCX** — internal hyperlinks и bookmarks; требует OOXML/Word/LibreOffice QA.
- **PDF** — производный publication format; проверить сохранение internal links и page destinations.
- **JSON spec** — источник сборки и audit trail, не пользовательский финал.

## 6. Минимальный source metadata block

`source_id, title, authority, identifier, type, jurisdiction, date, version/as_of, effective dates, retrieved_at, official_url/local_ref, sha256, inclusion_mode, reliability, limitations`

## 7. Не решаемые автоматически риски

- неверный юридический смысл при формально правильной цитате;
- неполный поиск adverse authority;
- поддельный первичный файл с корректным локальным hash;
- OCR error, который человек не проверил;
- изменение официального источника после retrieval;
- неправомерное воспроизведение полного copyrighted document;
- disclosure ограниченных данных.

Поэтому документ хранится вместе с validation report, source register и human audit status.
