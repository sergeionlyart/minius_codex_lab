---
name: legal-monitoring
description: Проведи полный правовой мониторинг уровня L3: общественная проблема, цель нормы, механизм, применение, данные, outcome/impact, причинность, root cause и измеримые рекомендации. Используй только для комплексной оценки регулирования; не запускай для простой правовой справки.
---

# Правовой мониторинг

## Contract

- **Job-to-be-done:** оценить действие регулирования от проблемы и механизма до outcome/impact и предложить проверяемые варианты улучшения.
- **Inputs:** паспорт акта/политики, период, общественная проблема, stakeholders, доступные источники и данные.
- **Outputs:** source register, theory of change, legal/implementation/data analysis, root causes и рекомендации.
- **Evidence and safety:** отделяй факт от гипотезы, оценивай причинную силу, минимизируй данные и фиксируй provenance.
- **Stop conditions:** остановись, если отсутствуют scope, baseline/denominator или доказательства не позволяют причинный вывод.
- **Acceptance test:** вручную проверь одну цепочку проблема → механизм → outcome и воспроизведи один показатель от источника.

## Главный вопрос

Привели ли правовая норма и деятельность ответственного органа к обоснованному, измеримому уменьшению общественной проблемы, ради которой регулирование было введено?

## Базовая причинная цепочка

`общественная проблема → причина → цель → норма → механизм → ответственный орган → действие/output → изменение поведения → outcome → impact → вывод → рекомендация`

Не считай конечным общественным результатом само принятие акта, создание органа, совещание, обучение, отчет, ИТ-систему или освоение бюджета.

## Адаптивная процедура

Полный мониторинг включает модули ниже, но глубина каждого определяется scope. Нерелевантный модуль не заполняй искусственно; объясни исключение.

### 1. Паспорт и проблема

- предмет, нормы, период, территория, органы, адресаты;
- общественная проблема, масштаб, affected groups, baseline;
- заявленная цель и ожидаемый результат;
- аналитически реконструированная цель, если официальная отсутствует;
- временной горизонт воздействия.

Не определяй проблему как «отсутствие закона», пока не установлена общественная потребность.

### 2. Реестр источников

Используй `$source-provenance`. Приоритизируй источники, проверяющие гипотезы. Веди reviewed-not-used list.

### 3. Вопросы и гипотезы

Для каждой гипотезы укажи:

- что должно быть установлено;
- supporting и falsifying evidence;
- необходимые источники/данные;
- альтернативные объяснения;
- acceptance/rejection criterion;
- текущий статус.

Не формируй финальные рекомендации до проверки ключевых гипотез.

### 4. Theory of change

Для каждой ключевой нормы: проблема, причина, mechanism, actor, expected behavior change, output, outcome, impact, timing, assumptions/external conditions.

Если цепочка разорвана, классифицируй разрыв: цель, адресат, механизм, орган, показатель, связь с проблемой.

### 5. Формально-юридический анализ

Проверь hierarchy, Constitution, international/EU obligations, internal consistency, gaps, conflicts, duplication, legal certainty, procedure, deadlines, competence, discretion, corruption risks, proportionality, remedies и practical enforceability.

Для дефекта: норма → дефект → практическое следствие → evidence → связь с проблемой → вариант устранения.

### 6. Реализация и практика

Используй `$case-law-analysis` и административные данные. Отдели defect of norm, interpretation, inconsistent practice, institutional execution, resources, digital/data gap, policy design и external factors.

### 7. Количественные данные

Используй `$quantitative-impact-analysis`. Раздели inputs/outputs/outcomes/impact. Проверь denominator, methodology, comparability, coverage и external factors. Не создавай false precision.

### 8. Stakeholders

Включай только фактически проведенные surveys/consultations. Опиши population, sample, selection, questions, period, biases и допустимую generalization. Субъективное восприятие не заменяет объективные данные.

### 9. Международный/ЕС и наука

Используй `$eu-acquis-analysis` и качественные исследования только для функционального решения конкретной причины. Не заимствуй норму из-за одного факта ее существования за рубежом.

### 10. Причинность

Для каждого ключевого impact claim:

- evidence и counterevidence;
- temporal sequence;
- alternative explanations;
- external factors;
- counterfactual: что было бы без нормы;
- возможные comparisons/trends/control groups;
- сила доказательств: strong, moderate, limited, contradictory, not confirmed, impossible;
- confidence: high, medium, low.

Корреляция и последовательность сами по себе не являются причинностью.

### 11. Оценка и root cause

Оцени relevance, evidence basis, logic, legal quality, enforceability, institutional capacity, consistency, outcome, efficiency, impact, sustainability, proportionality, side effects и data quality.

Построй: symptom → immediate cause → systemic root cause → consequences.

### 12. Рекомендации

Каждая рекомендация связывает:

`problem → root cause → evidence → action → responsible actor → legal/managerial instrument → resources → output → outcome → impact → indicator/baseline/target → deadline/reassessment → risks → priority`

Сначала проверь менее сложное достаточное решение: practice, clarification, subordinate act, procedure, integration, automation, data/indicator, function allocation. Закон меняй только при установленной необходимости.

## Обязательные артефакты

Список, схемы и минимальные поля — `references/monitoring-artifacts.md`. Финальный отчет нельзя объявлять завершенным, если критические артефакты отсутствуют; можно выдать interim report с явными пробелами.

## Итоговый отчет

Рекомендуемая структура:

1. Executive summary без новых фактов.
2. Проблема и масштаб.
3. Нормативное регулирование.
4. Реализация/практика.
5. Данные и их качество.
6. Stakeholders — только если исследованы.
7. ЕС/международный опыт — если релевантен.
8. Научные материалы — если релевантны.
9. Причинность и оценка результативности.
10. Root causes, conclusions и ranked recommendations.
11. Ограничения и missing-data register.
12. Приложения/evidence pack.

Для высокозначимого результата применяй `$verifiable-legal-document` и независимый `$legal-qa-audit`.
