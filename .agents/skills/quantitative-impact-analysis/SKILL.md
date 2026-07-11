---
name: quantitative-impact-analysis
description: >-
  Проанализируй статистические, административные и финансовые данные для
  юридической задачи: показатели, качество, сопоставимость, воспроизводимые
  расчеты, outcome/impact и осторожная причинность. Не используй при
  отсутствии достаточных данных для числового вывода.
---

# Количественный и impact-анализ

## Contract

- **Job-to-be-done:** получить воспроизводимые показатели и осторожную оценку связи intervention с outcome/impact.
- **Inputs:** исследовательский вопрос, dataset/source, indicator definitions, периоды, denominators и ограничения доступа.
- **Outputs:** data note, indicator dictionary, расчеты/код, uncertainty, альтернативные объяснения и выводы.
- **Evidence and safety:** минимизируй данные, фиксируй lineage, не публикуй персональные строки и не изображай correlation как causation.
- **Stop conditions:** остановись при неизвестном знаменателе, несовместимой методике, критических quality gaps или запрещенной обработке.
- **Acceptance test:** вручную воспроизведи один итоговый показатель из исходных строк и сверь округление/период.

## Принцип

Число без определения, знаменателя, периода, источника и методики не является доказательством. Не создавай иллюзию точности.

## Indicator dictionary

Для каждого показателя зафиксируй:

- name и substantive definition;
- type: input/activity/output/outcome/impact/context;
- unit и denominator;
- formula;
- data owner/source;
- collection method и frequency;
- coverage/population/sample;
- baseline, pre-change, post-change, current, target;
- methodology version и breaks in series;
- missingness/duplicates/outliers;
- comparability across time/regions/groups;
- external factors;
- uncertainty/limitations.

## Процедура

1. Свяжи показатель с конкретным звеном theory of change. Не используй activity metric как impact.
2. Сохрани raw data только в разрешенной зоне; не изменяй оригинал. Создай reproducible transform script/notebook и derived table.
3. Проверь schema, types, row counts, uniqueness, missing values, duplicates и impossible values.
4. Установи denominator и единицу наблюдения.
5. Проверь изменения методологии/coverage. При break in series не сравнивай напрямую без корректировки.
6. Раздели descriptive statistics и causal inference.
7. Для сравнения используй, где допустимо:
   - pre/post trend;
   - regions/bodies/groups;
   - interrupted time series;
   - comparable/control group;
   - sensitivity analysis;
   - alternative explanations.
8. Для privacy-sensitive data применяй minimization, aggregation и suppression small cells.
9. Сформируй table/figure с machine-readable source, кодом и checksum.
10. Каждый числовой claim добавь в `evidence/CLAIMS.csv` с evidence ref на dataset/table/script.

## Запрет ложной точности

Не рассчитывай/не публикуй доли, средние, темпы, correlations или trends, если:

- неизвестен denominator;
- выборка/coverage неизвестны;
- периоды несопоставимы;
- изменилась методика;
- единичные случаи выданы за общий массив;
- источник не позволяет воспроизвести расчет.

Используй диапазоны/qualitative assessment и маркируй approximate, когда это честнее.

## Causal evidence scale

- strong;
- moderate;
- limited;
- contradictory;
- not confirmed;
- impossible due to data quality/absence.

Confidence оцени отдельно: high/medium/low.

## Выходы

- indicator dictionary;
- data quality report;
- reproducible scripts;
- derived tables/charts;
- causal/alternative-explanation matrix;
- missing-data request specification;
- limitations ready for final report.

## Definition of done

Независимый аналитик может воспроизвести число из исходного разрешенного набора, понять методику и увидеть, какие выводы данные не позволяют делать.
