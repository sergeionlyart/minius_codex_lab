---
name: case-law-analysis
description: Сформируй воспроизводимый массив судебной/административной практики и проанализируй holdings, категории, согласованность и ограничения выборки. Используй при выводах о практике; не используй единичные решения как автоматическое обобщение.
---

# Анализ судебной и административной практики

## Contract

- **Job-to-be-done:** собрать воспроизводимый corpus решений и определить holdings, расхождения и пределы обобщения.
- **Inputs:** юрисдикция, органы/инстанции, период, правовой вопрос и inclusion/exclusion criteria.
- **Outputs:** протокол поиска, corpus rows, synthesis, adverse cases и ограничения выборки.
- **Evidence and safety:** используй точные локаторы и официальные источники; санитизируй внешние запросы и не раскрывай материалы дела.
- **Stop conditions:** остановись, если scope не определен, источник нельзя проверить или доступная выборка не позволяет заявленный вывод.
- **Acceptance test:** вручную повтори один поиск и проверь для трех решений реквизиты, finality, holding и locator.

## До поиска: протокол выборки

Зафиксируй в `research/case-law-protocol.md`:

- юридический вопрос и ключевые нормы;
- юрисдикцию и вид органа;
- инстанции;
- период;
- inclusion/exclusion criteria;
- search strings, synonyms и filters;
- способ дедупликации;
- finality/procedural status;
- стратегия полной выборки или sampling;
- известные ограничения доступа и representativeness.

Без протокола нельзя делать количественный вывод о практике.

## Поля corpus

Для каждого решения:

- `decision_id`;
- court/body, chamber, jurisdiction, instance;
- case number/official identifier;
- date;
- finality/status;
- norms;
- issue;
- material facts;
- holding/ratio;
- relevant obiter отдельно;
- outcome/remedy;
- category/tags;
- exact paragraph/page locator;
- official URL/local copy/hash;
- subsequent treatment/overruling, если известно;
- relevance и limitations.

## Процедура

1. Проверь, доступен ли официальный реестр и каковы ограничения доступа.
2. Выполни поиск по заранее зафиксированным словам; журналируй запросы и количество результатов.
3. Удали технические дубликаты, но сохрани связанные инстанции как отдельные записи.
4. Не смешивай:
   - разные юрисдикции;
   - разные инстанции;
   - окончательные/неокончательные решения;
   - процессуальные/материальные вопросы;
   - ratio и obiter;
   - решения до/после изменения нормы.
5. Извлеки holding своими словами и рядом точный supporting extract. Не приписывай суду более широкий тезис.
6. Классифицируй практику: consistent, dominant with exceptions, split, evolving, fragmented, insufficient sample.
7. Проверь adverse cases и последующую судьбу ключевых решений.
8. Количественные доли рассчитывай только при известном denominator и понятной полноте массива.
9. Объясни, что практика показывает о качестве нормы: clarity, enforceability, predictability, institutional defects.
10. Отдельно оцени, является ли проблема дефектом текста, толкования, неодинакового применения или исполнения.

## Выходы

- `research/case-law-protocol.md`;
- `research/case-law-corpus.csv` или `.jsonl`;
- category matrix;
- synthesis note;
- list of adverse/contrary authorities;
- statement of sample limitations.

## Definition of done

Другой исследователь может повторить поиск, понять включение/исключение каждого решения, проверить holding по точному фрагменту и увидеть, насколько допустимо обобщение.
