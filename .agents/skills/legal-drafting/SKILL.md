---
name: legal-drafting
description: >-
  Подготовь юридическую записку, заключение, проект нормы, письмо или отчет
  только на основе проверенного evidence ledger. Используй после evidence
  gate; не используй для первичного поиска источников.
---

# Юридическое drafting

## Contract

- **Job-to-be-done:** подготовить юридический draft из утвержденного evidence ledger без добавления непроверенных тезисов.
- **Inputs:** адресат, тип документа, язык, scope, evidence ledger, ограничения и критерий готовности.
- **Outputs:** структурированный draft, claim/evidence links, placeholders, риски и вопросы для утверждения.
- **Evidence and safety:** не исследуй заново из памяти, не скрывай adverse authority и соблюдай классификацию данных.
- **Stop conditions:** остановись, если нет минимального evidence gate, владельца финального текста или обязательного шаблона.
- **Acceptance test:** вручную выбери три существенных тезиса и проследи каждый до evidence unit и точного locator.

## Входной gate

До начала должны существовать:

- однозначный вопрос, адресат и дата актуальности;
- утвержденный outline/product type;
- source register;
- evidence ledger для ключевых тезисов;
- перечень adverse/counterevidence;
- список отсутствующих данных и допустимых assumptions;
- язык и ведомственные требования к форме.

Если gate не пройден, создай skeleton с placeholders и верни пробелы coordinator, а не заполняй их памятью модели.

## Типы документов

Адаптируй структуру к продукту:

- legal memorandum/opinion;
- служебная/аналитическая записка;
- проект нормативно-правового акта/поправки;
- сравнительная таблица;
- пояснительная записка/обоснование;
- официальный ответ/письмо;
- правовой мониторинговый отчет;
- information request/ТЗ на данные.

## Процедура

1. Зафиксируй audience и решение, которое документ должен поддержать.
2. Создай outline; каждый раздел должен отвечать на вопрос, а не повторять источники.
3. Назначь каждому material proposition `claim_id` и `claim_type`:
   - fact;
   - legal_proposition;
   - numeric;
   - quotation;
   - interpretation;
   - assumption;
   - recommendation.
4. Пиши conclusion-first. После вывода укажи authority/evidence, analysis, contrary position, limitation и consequence.
5. Для нормы указывай exact article/part/point и version/as-of.
6. Для практики отделяй holding от собственной интерпретации и указывай статус/ограничение выборки.
7. Для цифры — period, unit, denominator, source и method.
8. Рекомендацию связывай с root cause, actor, instrument, deadline, indicator и risk.
9. Неподтвержденное:
   - удалить;
   - или пометить `[ПОДЛЕЖИТ ПРОВЕРКЕ: ...]`;
   - или явно обозначить как assumption с consequence.
10. Выполни consistency pass: terminology, definitions, dates, cross-references, annexes, duplicate claims.
11. Для проверяемого результата передай structured spec в `$verifiable-legal-document`.
12. Перед выдачей запусти `$legal-qa-audit`.

## Язык

- Официальные документы для органов Украины — украинский по умолчанию.
- Внутренняя записка — язык поручения.
- Цитаты — оригинал; перевод маркируется.
- Избегай неопределенных глаголов «усовершенствовать/усилить/активизировать» без конкретного действия.

## Проекты норм

Для точной редакции:

- укажи изменяемый акт и структурную единицу;
- покажи current text и proposed text;
- проверь consequential amendments, definitions, competence, procedure, transition, entry into force и implementation resources;
- отдели drafting note от текста нормы;
- не заявляй отсутствие коллизий без проверки смежных актов.

## Definition of done

В тексте нет нового факта без evidence ref, выводы не сильнее доказательств, adverse authority раскрыта, рекомендации операциональны, а document status и необходимость human approval явны.
