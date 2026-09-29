# Rent Market Tracker для Kilo Code + Google Sheets

## Цель

Собирать объявления аренды квартир с сайта из списка:

- 4zida.rs
- cityexpert.rs
- halooglasi.com
- imovina.net
- nekretnine.rs
- oglasi.rs

и хранить их в Google Sheets для:

- сравнения по цене, району, условиям и рискам
- отслеживания появления/исчезновения объявлений
- оценки аренды ЖК, коммуналки, залога, комиссии и минимального срока
- аналитики по частоте появления и ценовым трендам

## Параметры отбора

Объявление должно попадать в выборку только если:

1. Можно с животными
2. Мебелирована
3. 3 комнаты + кухня
4. Цена до 900 EUR
5. Район — Белград
6. Тип жилья — квартира/дом
7. Есть стиральная и посудомоечная машина

Дополнительно:

- 4 человека могут жить комфортно
- жилплощадь и этаж важны для оценки
- хорошая кухня, холодильник, плита, горячая вода, Wi‑Fi

## Архитектура решения

### 1. Источники данных

- Сайты из списка
- Парсер (Python + requests/BeautifulSoup/Scrapy/Playwright)
- Kilo Code как оркестратор задач и наблюдения за процессом
- Local MCP server для взаимодействия с Google Sheets API

### 2. Поток данных

1. Kilo запускает задачу парсинга по списку доменов
2. Парсер собирает объявление, извлекает все поля
3. Скрипт нормализует значения и приводит к единому формату
4. Скрипт дедуплицирует по `ad_id` или `url`
5. Если объявление новое — добавляется в Google Sheets
6. Если объявление уже есть — обновляется статус и история цены
7. Kilo оценивает риски и делает сводку по рынку

## Рабочая структура Google Sheets

Нужно сделать один документ с несколькими листами.

### Лист 1: `Объявления_активные`

Основной лист со всеми актуальными объявлениями.

Колонки:

- `ad_id`
- `site`
- `title`
- `url`
- `region`
- `district`
- `address`
- `property_type`
- `rooms_count`
- `kitchen_separate`
- `furnished`
- `pets_dog_allowed`
- `pets_cat_allowed`
- `pet_fee_eur`
- `washer_machine`
- `dishwasher`
- `wifi`
- `hot_water`
- `fridge`
- `stove`
- `oven`
- `area_m2`
- `floor`
- `total_floors`
- `price_eur`
- `price_per_month_eur`
- `currency`
- `utilities_eur`
- `electricity_included`
- `deposit_eur`
- `deposit_refundable`
- `commission_eur`
- `other_fees_eur`
- `total_monthly_cost_eur`
- `three_week_price_eur`
- `min_rent_term_months`
- `rent_paid_3_weeks_only`
- `available_from_date`
- `first_seen_date`
- `last_updated_date`
- `status`
- `status_reason`
- `days_on_market`
- `is_match`
- `match_score`
- `risk_score`
- `notes`
- `created_at`
- `updated_at`

### Лист 2: `История_объявлений`

Полная история каждого объявления по датам.

Колонки:

- `ad_id`
- `site`
- `url`
- `date_snapshot`
- `price_eur`
- `utilities_eur`
- `deposit_eur`
- `status`
- `was_seen`
- `last_updated_date`
- `source_html_hash`
- `notes`

Это нужно для:

- отслеживания изменения цены
- поиска ценовых всплесков
- фиксирования момента исчезновения объявления
- определения длительности присутствия на рынке

### Лист 3: `Чеклист_осмотра`

Заполняется вручную после просмотра квартиры.

Колонки:

- `ad_id`
- `view_date`
- `agent_name`
- `landlord_contact`
- `address_checked`
- `inside_visit_done`
- `condition_ok`
- `noise_level`
- `safety_level`
- `pets_allowed_verified`
- `washer_machine_verified`
- `dishwasher_verified`
- `kitchen_complete`
- `water_hot`
- `wifi_present`
- `repair_quality`
- `summary_risk`
- `follow_up_needed`
- `final_decision`
- `next_action`

### Лист 4: `Аналитика_рынка`

Сводка и метрики рынка.

Колонки:

- `date`
- `site`
- `avg_price_eur`
- `median_price_eur`
- `min_price_eur`
- `max_price_eur`
- `ads_total`
- `ads_match_total`
- `ads_with_pets_allowed`
- `ads_with_washer`
- `ads_with_dishwasher`
- `ads_with_furniture`
- `new_ads_per_day`
- `removed_ads_per_day`
- `avg_days_on_market`
- `avg_deposit_eur`
- `avg_utilities_eur`
- `avg_commission_eur`
- `risk_summary`

### Лист 5: `Сводка_по_районам`

Рейтинг районов Белграда по ценам и качеству.

Колонки:

- `district`
- `ads_total`
- `avg_price_eur`
- `min_price_eur`
- `max_price_eur`
- `avg_area_m2`
- `avg_days_on_market`
- `matches_quality_score`
- `comment`

### Лист 6: `Архив`

Все объявления, которых больше нет в активных и которые:

- сданы
- удалены
- скрыты
- архивированы вручную

Колонки:

- `ad_id`
- `site`
- `url`
- `last_seen_date`
- `status`
- `archive_reason`
- `final_price_eur`
- `duration_days`
- `notes`

## Формулы и вычисляемые поля

### Поля расчёта

- `days_on_market = (today - first_seen_date)`
- `price_per_m2 = price_eur / area_m2`
- `total_monthly_cost_eur = price_eur + utilities_eur + other_fees_eur + commission_eur`
- `match_score` = числовая оценка соответствия критериям:
  - pets allowed
  - furnished
  - rooms count
  - kitchen
  - washer/dishwasher
  - district match
  - price <= 900
- `risk_score` = оценка риска по параметрам:
  - цена слишком низкая
  - заброшенное или странное описание
  - нет фото/нет точного адреса
  - комиссия скрыта
  - срок аренды непонятен

### Статусы объявления

- `active`
- `updated`
- `price_changed`
- `disappeared`
- `rented`
- `archived`
- `rejected`

## Критерии отбора `is_match`

Флаг должен быть `TRUE`, если объявление соблюдает все обязательные условия:

- `pets_dog_allowed = TRUE` OR `pets_cat_allowed = TRUE` (в идеале оба)
- `rooms_count >= 3`
- `kitchen_separate = TRUE`
- `furnished = TRUE`
- `washer_machine = TRUE`
- `dishwasher = TRUE`
- `price_eur <= 900`
- `region = "Belgrade"` OR `district` in region whitelist
- `property_type in ("apartment", "house")`

## Риски и аналитика

### Что важно сравнивать

- аренда + коммуналка + комиссия + залог
- минимальный срок аренды
- есть ли оплата за 3 недели или только за месяц
- годится ли квартира под проживание четырёх человек
- есть ли скрытая доплата за животных
- цена на 1 м²
- сколько дней объявление висит на рынке

### Аналитика, которую надо смотреть

- средняя цена за квартал
- медиана по району
- средняя длительность жизни объявления
- сколько объявлений исчезло за неделю
- сколько новых объявлений появилось
- какое число объявлений улучшается или ухудшается по цене
- какой район самый дешевый/дорогой
- какой район чаще всего подходит под критерии

## Google Sheets API: что использовать

Для этой задачи нужен набор стандартных API вызовов:

- `spreadsheets.get` — получить структуру документа и листы
- `spreadsheets.values.get` — прочитать строки
- `spreadsheets.values.update` — обновить диапазон
- `spreadsheets.values.append` — добавить новую строку
- `spreadsheets.batchUpdate` — менять листы, стили, заголовки, freeze panes, сортировку
- `spreadsheets.values.batchUpdate` — пакетное обновление нескольких блоков

Для автоматизации удобно:

- один лист для входного потока
- один лист для аналитики
- один лист для статусов и истории

## Как это внедрить с Kilo Code

### 1. Local MCP server

Использовать имеющийся проект в этой папке как слой доступа к Google Sheets API.

Kilo Code должен управлять запуском и вызовом MCP-сервера, а не напрямую писать JSON конфиг в глобальный файл `kilo.jsonc`.

Для вашей локальной версии Kilo нужно использовать команду CLI:

- `kilo mcp add ...`
- `kilo mcp list`
- `kilo mcp auth ...`

не вручную кладя `mcpServers` в глобальный `kilo.jsonc`.

### 2. Python scraper

- `scrape_sites.py` — запуск парсинга всех сайтов
- `normalize_listing.py` — нормализация и фильтрация
- `google_sheets_sync.py` — запись в Sheets
- `market_analysis.py` — аналитика и сводки
- `risk_scoring.py` — вычисление score

### 3. Схема логики запуска

- daily run: `kilo run "обнови рынок аренды для Белграда и заполни Google Sheets"`
- weekly run: `kilo run "сделай сверку рынка и обнови аналитические листы"`
- ad audit: `kilo run "проверь все активные объявления и найди те, которые не соответствуют требованиям"`

## Пример строки объявления после нормализации

```json
{
  "ad_id": "nekretnine_123456",
  "site": "nekretnine.rs",
  "title": "3-bedroom apartment in Belgrade",
  "url": "https://...",
  "region": "Belgrade",
  "district": "Vracar",
  "property_type": "apartment",
  "rooms_count": 3,
  "kitchen_separate": true,
  "furnished": true,
  "pets_dog_allowed": true,
  "pets_cat_allowed": true,
  "pet_fee_eur": 50,
  "washer_machine": true,
  "dishwasher": true,
  "wifi": true,
  "area_m2": 85,
  "floor": 3,
  "total_floors": 8,
  "price_eur": 780,
  "utilities_eur": 120,
  "deposit_eur": 1560,
  "commission_eur": 0,
  "other_fees_eur": 30,
  "min_rent_term_months": 6,
  "status": "active",
  "first_seen_date": "2026-09-21",
  "last_updated_date": "2026-09-21",
  "risk_score": 14,
  "match_score": 96
}
```

## Рекомендуемая итоговая структура документа

Один Excel файл с названием:

- `Belgrade_Rent_Market_Tracker.xlsx`

Листы:

1. `Объявления_активные`
2. `История_объявлений`
3. `Чеклист_осмотра`
4. `Аналитика_рынка`
5. `Сводка_по_районам`
6. `Архив`
7. `Настройки`

## Следующий оптимальный шаг

Дальше я могу сделать для вас одну из двух вещей:

1. подготовить конкретный шаблон для Google Sheets в виде CSV/JSON-структуры, готовой к импорту;
2. начать писать код проекта в этом репозитории — парсер + нормализация + синхронизация с Google Sheets через local MCP.

Если хотите, я могу прямо сейчас сделать второй вариант и начать создавать рабочую структуру проекта под Kilo Code в этой папке.
