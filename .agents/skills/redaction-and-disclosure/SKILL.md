---
name: redaction-and-disclosure
description: >-
  Классифицируй, минимизируй и подготовь материалы к веб-поиску, внешнему репо
  или выдаче: redaction, metadata, secrets, personal/restricted data и
  disclosure log. Используй перед внешним действием; не используй как замену
  human approval и не понижай класс данных.
---

# Redaction и допустимость раскрытия

## Contract

- **Job-to-be-done:** создать минимизированную копию и обоснованное решение о допустимости конкретного раскрытия.
- **Inputs:** материал, цель/получатель, data classification, правовые и организационные правила.
- **Outputs:** redacted copy, redaction log, residual-risk findings и требуемое human approval.
- **Evidence and safety:** оригинал не изменяй; учитывай текст, metadata, вложения, скрытые слои и косвенную идентификацию.
- **Stop conditions:** останови раскрытие при неизвестной цели, полномочиях, классе, неудаляемом риске или отсутствии approval.
- **Acceptance test:** вручную проверь копию поиском удаленных значений и просмотром metadata/рендера отдельным reviewer.

## Цель

Снизить объем раскрываемых данных до минимально необходимого и сделать решение о раскрытии проверяемым. Этот skill не заменяет решение уполномоченного подразделения по безопасности/защите данных.

## Процедура

1. Определи target action: web query, remote push, external email/export, public release, subagent/MCP.
2. Определи data class по `SECURITY.md` и внутренней политике. Не понижай класс.
3. Создай inventory чувствительных элементов:
   - personal identifiers;
   - case/party names;
   - addresses/contact/bank/health data;
   - secrets/tokens/keys;
   - official-use/restricted markings;
   - investigation/sealed/professional secrets;
   - local paths/usernames;
   - hidden metadata/comments/tracked changes;
   - embedded files/macros.
4. Проверь necessity каждого элемента. Удали, обобщи, псевдонимизируй или замени surrogate ID.
5. Для веб-запроса сформируй sanitized query, не позволяющий восстановить конкретное дело.
6. Для Git проверь staged set, а не только working tree:

```bash
python3 scripts/check_repo_safety.py --staged
```

7. Для DOCX/PDF проверь metadata, comments, hidden text и attachments; после redaction повторно извлеки текст/metadata для контроля.
8. Создай disclosure log:
   - action/date/actor;
   - files/fields;
   - class;
   - redactions;
   - legal/organizational basis;
   - recipient/system;
   - approval;
   - residual risk.
9. Если безопасная минимизация невозможна, запрети внешнее действие и предложи локальный/offline путь.

## Redaction quality

Черный прямоугольник поверх текста не считается надежной redaction, если исходный текст остается извлекаемым. Для каждого формата используй удаление содержимого и проверку повторным извлечением.

## Выходы

- sanitized copy;
- redaction map, хранимый отдельно и более строго;
- disclosure log;
- список residual risks;
- решение: allow / allow with conditions / deny / needs authorized review.

## Definition of done

Внешний набор содержит только необходимое, скрытые слои проверены, решение и approval зафиксированы, а исходник остался неизменным в разрешенной защищенной зоне.
