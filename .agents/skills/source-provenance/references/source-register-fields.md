# Source register — обязательные поля и правила

## Канонические поля

| Поле | Назначение |
|---|---|
| `source_id` | Устойчивый локальный ID, например `SRC-UA-001` |
| `title` | Официальное или библиографическое название |
| `source_type` | НПА, редакция, судебное решение, dataset, отчет, научная статья и т. п. |
| `authority` | Орган, суд, автор или владелец данных |
| `jurisdiction` | Украина, ЕС, Совет Европы, государство и т. п. |
| `legal_status` | Юридическая сила/обязательность/процессуальный статус |
| `document_date` | Дата акта/решения/публикации |
| `effective_from` / `effective_to` | Период действия редакции, если применимо |
| `period_covered` | Период, к которому относятся данные/выводы |
| `retrieved_at` | Абсолютная дата и время получения |
| `official_url` | Официальный URL, если доступен |
| `local_path` | Относительный путь к разрешенной локальной копии |
| `sha256` | SHA-256 конкретного файла/снимка |
| `locator_scheme` | Статья/часть/пункт, paragraph, page, row/cell и т. п. |
| `language` | Язык оригинала |
| `reliability` | High/medium/low/needs-verification с обоснованием |
| `relevance` | Primary/supporting/context/adverse/reviewed-not-used |
| `limitations` | Неполнота, неизвестная редакция, access limits, methodology и т. п. |
| `hypothesis_or_claim` | Какие вопросы/claims источник способен проверять |
| `verification_status` | verified / machine-extracted / needs-human-verification |
| `notes` | Только необходимые пояснения; не заменяют evidence unit |

## Идентификаторы

- ID не переиспользуется после удаления источника.
- Разные редакции, переводы и локальные снимки получают разные `source_id`.
- Связь редакций фиксируется отдельным полем/заметкой, а не скрывается дедупликацией.
- URL без прочитанного содержания и locator не считается доказательством.

## Минимальная запись для material claim

Запись пригодна для существенного тезиса только при наличии: `source_id`, title, authority,
status, applicable date/version, retrieved_at, exact locator, official URL или local copy,
verification status и limitations. Для локальной копии обязателен hash.

## Reviewed-not-used

Не удаляй просмотренный источник. Укажи одну из причин: неверный период/редакция,
нерелевантность, дубликат, отсутствие первичного текста, недостаточная надежность,
неподтвержденная методика, отсутствие нужного тезиса или conflict unresolved.
