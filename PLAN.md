# План реализации проекта

## Цель

Автоматический сбор, парсинг, нормализация и загрузка объявлений аренды квартир в Белграде в Google Sheets через MCP. Все данные на русском языке. Kilo сам извлекает информацию из объявлений, заполняет таблицу, отслеживает изменения и ведёт аналитику.

---

## Этап 0: Подготовка окружения

### 0.1 Google Cloud и MCP
- [x] Создан проект `kilocode-mcp-google-workspace`
- [x] Локальный MCP-сервер готов (`server.py`, `venv`)
- [ ] Создать Service Account в Google Cloud Console
- [ ] Скачать `service-account-key.json` и положить в `kilocode-mcp-google-workspace/`
- [ ] Дать сервисному аккаунту права `Editor` на Google Таблицу
- [ ] Перезапустить Kilo, убедиться что MCP-сервер появился в `/mcp`

### 0.2 Google Таблица
- [ ] Создать таблицу `Квартиры Белград`
- [ ] Создать 4 листа: `Объявления`, `Аналитика`, `Чек-лист_осмотра`, `Архив`
- [ ] Заполнить заголовки в `Объявления` (строки 1)
- [ ] Добавить сервисный аккаунт как редактора таблицы

---

## Этап 1: Парсер сайтов

### 1.1 halooglasi.com

**Страница поиска (уже отфильтрована):**
```
https://www.halooglasi.com/nekretnine/izdavanje-stanova/beograd/trosoban?cena_d_to=900&cena_d_unit=4&namestenost_id_l=562
```

**Что парсим:**
- ID объявления (из URL или скрытого поля)
- Ссылка на объявление
- Заголовок
- Район
- Адрес
- Цена аренды (EUR/мес)
- Площадь (м²)
- Этаж
- Количество комнат
- Тип жилья
- Описание объявления
- Условия: животные, мебель, техника

**Пример объявления:**
```
https://www.halooglasi.com/nekretnine/izdavanje-stanova/izdajem-stan-na-altini/5425647715450?kid=4&sid=1790076287624
```

**Технические заметки:**
- Сайт может быть SPA — потребуется Playwright/Puppeteer
- Проверить, есть ли API эндпоинты
- Если есть пагинация — обработать все страницы

### 1.2 imovina.net

**Страница поиска:**
```
https://imovina.net/pretraga-nekretnina/izdavanje/?offerType%5B%5D=3&extras%5B%5D=35&mainRegion=1&subRegionText=&surfaceFrom=&surfaceTo=&priceFrom=&priceTo=900&currency=EUR&floorFrom=&floorTo=&sort=5&phone=&search=%D0%9F%D0%9E%D0%98%D0%A1%D0%9A&filterName=&filtersList=
```

**Что парсим:**
- ID объявления
- Ссылка
- Район
- Адрес
- Цена аренды
- Площадь
- Этаж
- Количество комнат
- Мебель (из фильтров и описания)
- Животные (из описания)
- Техника (стиральная, посудомоечная — из описания)

**Пример объявления:**
```
https://imovina.net/nekretnina/izdavanje/trosoban-stan_beograd__borca/1387449/
```

### 1.3 airbnb.ru (ru.airbnb.com)

**Страница поиска:**
```
https://ru.airbnb.com/s/homes?adults=4&pets=2&min_beds=3&price_max=900&room_types%5B%5D=Entire%20home%2Fapt&location_search=NEARBY&ne_lat=44.95272015018647&sw_lat=44.69185421799102&ne_lng=20.786672112868843&sw_lng=20.262115088436275
```

**Что парсим:**
- ID объявления (из URL)
- Ссылка
- Название
- Район
- Цена за ночь/месяц
- Количество спален (должно быть ≥3)
- Вместимость (≥4 человек)
- Удобства (wifi, стиральная, посудомоечная, кухня)
- Разрешение животных
- Тип жилья

**Пример объявления:**
```
https://ru.airbnb.com/rooms/996374153688771589?adults=4&pets=2&check_in=2026-11-05&check_out=2026-11-06
```

**Технические заметки:**
- Airbnb активно блочит парсинг
- Использовать Playwright с stealth-плагином
- Задержки между запросами
- Headless режим с эмуляцией браузера

### 1.4 oglasi.rs

**Страница поиска:**
```
https://www.oglasi.rs/nekretnine/izdavanje-stanova/beograd?pr%5Be%5D=900&pr%5Bc%5D=EUR&d%5BSobnost%5D%5B0%5D=Trosoban&d%5BOpremljenost%5D%5B0%5D=Name%C5%A1ten&d%5BInternet%5D=1
```

**Что парсим:**
- ID объявления
- Ссылка
- Район
- Адрес
- Цена аренды
- Площадь
- Этаж
- Мебель
- Интернет
- Описание для извлечения животных/техники

**Пример объявления:**
```
https://www.oglasi.rs/oglas/03-3945142/zemun-zemunske-kapije-68682
```

---

## Этап 2: Нормализация данных

### 2.1 Единый формат

Все данные из разных сайтов приводятся к единому формату перед записью в таблицу:

```python
{
    "id": str,                    # Уникальный ID
    "platform": str,              # Площадка
    "url": str,                   # Ссылка
    "title": str,                 # Заголовок (на русском)
    "district": str,              # Район Белграда
    "address": str,               # Адрес
    "property_type": str,         # Квартира/Дом
    "rooms": int,                 # Количество комнат (должно быть 3)
    "kitchen": bool,              # Есть кухня
    "area_m2": float,             # Площадь
    "floor": str,                 # Этаж
    "price_eur": float,           # Цена аренды
    "currency": str,              # EUR
    "utilities_eur": float,       # Коммуналка
    "electricity_included": bool, # Электричество входит
    "deposit_eur": float,         # Залог
    "deposit_refundable": bool,   # Возвращается ли залог
    "other_payments": str,        # Другие платежи
    "total_cost_eur": float,      # Итоговая стоимость
    "payment_3_weeks": bool,      # Оплата за 3 недели
    "min_lease_months": str,      # Мин срок аренды
    "dogs_allowed": bool,         # Собака разрешена
    "cats_allowed": bool,         # Кошка разрешена
    "pet_fee_eur": float,         # Доплата за животных
    "fridge": bool,               # Холодильник
    "stove": bool,                # Плита
    "oven": bool,                 # Духовка
    "washing_machine": bool,      # Стиральная машина
    "dishwasher": bool,           # Посудомоечная машина
    "hot_water": bool,            # Горячая вода
    "wifi": bool,                 # Wi-Fi
    "beds_for_all": bool,         # Кровати для всех
    "furniture_desc": str,        # Описание мебели
    "first_seen": date,           # Дата первого появления
    "found_date": date,           # Дата нахождения
    "last_updated": date,         # Дата последнего обновления
    "rented_date": date,          # Дата сдачи (если сдано)
    "days_on_market": int,        # Дней на рынке
    "current_price_eur": float,   # Текущая цена
    "price_change_eur": float,    # Изменение цены
    "status": str,                # Активно/Исчезло/Сдано/Цена изменилась
    "frequency_per_day": float,   # Частота появления в день
    "notes": str                  # Примечания
}
```

### 2.2 Извлечение из описаний

Kilo должен анализировать текст объявления и извлекать:
- Разрешение животных: искать ключевые слова `собака`, `кошка`, `животные`, `pet friendly`, `допускаются животные`
- Мебель: `меблирован`, `мебель`, `кровать`, `диван`, `стол`
- Техника: `стиральная машина`, `посудомоечная машина`, `холодильник`, `плита`, `духовка`, `wifi`, `интернет`
- Этаж: `этаж`, `floor`, `поверх`
- Площадь: `м²`, `кв.м`, `m2`
- Цена: искать числовые значения с `EUR`, `€`, `евро`

---

## Этап 3: Запись в Google Sheets

### 3.1 Структура таблицы

**Лист `Объявления`** (основной):
- 40+ колонок согласно VISION.md
- Заголовки на русском
- Данные на русском

**Лист `Аналитика`**:
- Сводные показатели по всем объявлениям
- Формулы для автоматического подсчёта

**Лист `Чек-лист_осмотра`**:
- Шаблон для ручного заполнения при осмотре

**Лист `Архив`**:
- Закрытые объявления

### 3.2 Логика записи

1. При первом нахождении объявления:
   - Проверить дедупликацию по `ID_объявления + Площадка`
   - Если новое — добавить строку
   - Заполнить `Дата_первого_появления`, `Дата_нашли`, `Статус = Активно`

2. При повторном сканировании:
   - Найти по ID
   - Обновить `Цена_сейчас_EUR`, `Дата_последнего_обновления`, `Статус`
   - Если цена изменилась → `Статус = Цена_изменилась`
   - Если объявление исчезло → `Статус = Исчезло`, `Дата_сдачи` пусто

3. При обнаружении что объявление сдано:
   - `Статус = Сдано`, `Дата_сдачи = сегодня`

### 3.3 Инструменты MCP для записи

- `update_cells` — обновление одной строки
- `batch_update_cells` — пакетное обновление нескольких строк
- `add_rows` — добавление новых строк
- `list_sheets` — проверка существования листов
- `get_sheet_data` — чтение данных для дедупликации

---

## Этап 4: Парсер архитектура

### 4.1 Структура проекта

```
квартиры/
├── VISION.md                    # Документация проекта
├── MCP_SETUP.md                 # Инструкция по MCP
├── PLAN.md                      # Этот файл
├── kilocode-mcp-google-workspace/
│   ├── server.py                # MCP сервер (уже есть)
│   ├── mcp_settings.json        # Конфиг MCP
│   ├── service-account-key.json # Ключ Service Account
│   └── venv/                    # Виртуальное окружение
├── parsers/                     # Папка с парсерами (создать)
│   ├── __init__.py
│   ├── base.py                  # Базовый класс парсера
│   ├── halooglasi.py            # Парсер halooglasi.com
│   ├── imovina.py               # Парсер imovina.net
│   ├── airbnb.py                # Парсер airbnb.ru
│   └── oglasi.py                # Парсер oglasi.rs
├── models/                      # Модели данных (создать)
│   ├── __init__.py
│   └── listing.py               # Модель объявления
├── utils/                       # Утилиты (создать)
│   ├── __init__.py
│   ├── translator.py            # Перевод на русский
│   ├── extractor.py             # Извлечение данных из текста
│   └── sheets_client.py         # Обёртка над MCP для работы с таблицей
├── config.py                    # Конфигурация (URL таблицы и т.д.)
└── main.py                      # Главный скрипт запуска
```

### 4.2 Базовый парсер

```python
# parsers/base.py
from abc import ABC, abstractmethod
from models.listing import Listing

class BaseParser(ABC):
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
    
    @abstractmethod
    def get_listing_urls(self) -> list[str]:
        """Получить список URL объявлений со страницы поиска"""
        pass
    
    @abstractmethod
    def parse_listing(self, url: str) -> Listing:
        """Парсить одно объявление и вернуть модель Listing"""
        pass
    
    def parse_all(self) -> list[Listing]:
        """Парсить все объявления со страницы поиска"""
        urls = self.get_listing_urls()
        listings = []
        for url in urls:
            try:
                listing = self.parse_listing(url)
                listings.append(listing)
            except Exception as e:
                print(f"Ошибка парсинга {url}: {e}")
        return listings
```

### 4.3 Модель объявления

```python
# models/listing.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class Listing:
    id: str
    platform: str
    url: str
    title: str
    district: str
    address: str
    property_type: str
    rooms: int
    kitchen: bool
    area_m2: Optional[float]
    floor: str
    price_eur: float
    currency: str = "EUR"
    utilities_eur: Optional[float] = None
    electricity_included: bool = False
    deposit_eur: Optional[float] = None
    deposit_refundable: bool = True
    other_payments: str = ""
    total_cost_eur: Optional[float] = None
    payment_3_weeks: bool = False
    min_lease_months: str = ""
    dogs_allowed: bool = False
    cats_allowed: bool = False
    pet_fee_eur: float = 0.0
    fridge: bool = False
    stove: bool = False
    oven: bool = False
    washing_machine: bool = False
    dishwasher: bool = False
    hot_water: bool = False
    wifi: bool = False
    beds_for_all: bool = False
    furniture_desc: str = ""
    first_seen: date = None
    found_date: date = None
    last_updated: date = None
    rented_date: Optional[date] = None
    days_on_market: int = 0
    current_price_eur: float = 0.0
    price_change_eur: float = 0.0
    status: str = "Активно"
    frequency_per_day: float = 0.0
    notes: str = ""
    
    def to_sheet_row(self) -> list:
        """Преобразовать в строку для Google Sheets"""
        return [
            self.id,
            self.platform,
            self.url,
            self.first_seen or "",
            self.found_date or "",
            self.last_updated or "",
            self.rented_date or "",
            self.days_on_market,
            self.district,
            self.address,
            self.property_type,
            self.rooms,
            self.kitchen,
            self.area_m2 or "",
            self.floor,
            self.price_eur,
            self.currency,
            self.utilities_eur or "",
            self.electricity_included,
            self.deposit_eur or "",
            self.deposit_refundable,
            self.other_payments,
            self.total_cost_eur or "",
            self.payment_3_weeks,
            self.min_lease_months,
            self.dogs_allowed,
            self.cats_allowed,
            self.pet_fee_eur or "",
            self.fridge,
            self.stove,
            self.oven,
            self.washing_machine,
            self.dishwasher,
            self.hot_water,
            self.wifi,
            self.beds_for_all,
            self.furniture_desc,
            self.current_price_eur or self.price_eur,
            self.price_change_eur,
            self.status,
            self.frequency_per_day,
            self.notes
        ]
```

---

## Этап 5: Интеграция с Google Sheets через MCP

### 5.1 Обёртка над MCP

```python
# utils/sheets_client.py
from typing import List, Dict, Any
from datetime import date

class SheetsClient:
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Объявления"
    
    def get_existing_ids(self) -> Dict[str, str]:
        """Получить словарь {ID_объявления: Площадка} для дедупликации"""
        # Использовать get_sheet_data
        pass
    
    def append_listing(self, listing) -> Dict:
        """Добавить новое объявление"""
        # Использовать add_rows + update_cells
        pass
    
    def update_listing(self, row_index: int, listing) -> Dict:
        """Обновить существующее объявление"""
        # Использовать update_cells
        pass
    
    def batch_append(self, listings: List) -> Dict:
        """Пакетное добавление объявлений"""
        # Использовать batch_update_cells
        pass
```

### 5.2 Запуск парсера через Kilo

Kilo должен иметь возможность запускать парсер командой:

```
Запусти парсер halooglasi
Запусти парсер imovina
Запусти парсер airbnb
Запусти парсер oglasi
Запусти все парсеры
```

---

## Этап 6: Отслеживание и аналитика

### 6.1 Периодический запуск

Использовать `schedule_wakeup` для периодического запуска парсеров:
- Интервал: каждые 6-12 часов
- При запуске: проверить все активные объявления, обновить цены/статусы

### 6.2 Формулы в таблице

В листе `Аналитика` Kilo должен заполнять:
- `Всего_объявлений` — COUNT всех строк
- `Активных_сейчас` — COUNTIF по статусу
- `Средняя_цена_EUR` — AVERAGEIF по активным
- `Медиана_цены_EUR` — медиана активных
- `Минимум_EUR` — MIN по активным
- `Максимум_EUR` — MAX по активным
- `Частота_появления_в_день` — среднее новых в день
- `Конверсия_в_сдачу_%` — отношение сданных к общему
- `Среднее_время_до_сдачи_дней` — среднее дней на рынке у сданных

### 6.3 Изменения цен

Kilo отслеживает:
- Если `Цена_сейчас_EUR != Цена_аренды_EUR` → `Статус = Цена_изменилась`
- Записывает историю изменений в `Примечания`
- Анализирует тренд: падает/растёт/стабильно

### 6.4 Исчезновение объявлений

- При повторном сканировании, если объявление не найдено на сайте:
  - `Статус = Исчезло`
  - `Дата_последнего_обновления = сегодня`
  - `Дней_на_рынке` считается до этой даты

---

## Этап 7: Перевод и нормализация

### 7.1 Перевод на русский

Kilo должен автоматически переводить:
- Названия районов Белграда на русский
- Типы жилья
- Описания удобств
- Условия аренды

### 7.2 Нормализация значений

- Даты: все в формате `YYYY-MM-DD`
- Цены: все в EUR
- Булевы значения: `да/нет` или `TRUE/FALSE`
- Районы: стандартизированный список Белграда

---

## Этап 8: Тестирование

### 8.1 Юнит-тесты

Для каждого парсера:
- Тест на извлечение ID
- Тест на извлечение цены
- Тест на извлечение района
- Тест на извлечение удобств

### 8.2 Интеграционные тесты

- Запуск парсера на 1 странице поиска
- Проверка записи в Google Sheets
- Проверка дедупликации
- Проверка обновления цен

### 8.3 Тестовые данные

Использовать предоставленные примеры объявлений для тестирования:
- halooglasi: `5425647715450`
- imovina: `1387449`
- airbnb: `996374153688771589`
- oglasi: `03-3945142`

---

## Этап 9: Деплой и автоматизация

### 9.1 Запуск парсера

Способ 1: Вручную через Kilo
```
Запусти парсер halooglasi
```

Способ 2: Автоматически через `schedule_wakeup`
```
Запусти все парсеры каждые 8 часов
```

### 9.2 Мониторинг

- Логи запусков сохранять в файл `parsers/logs/`
- Ошибки парсинга логировать с указанием URL
- Статистика: сколько объявлений найдено, добавлено, обновлено

### 9.3 Алерты

Kilo может отправлять уведомления если:
- Найдено новое объявление под фильтр
- Цена на отслеживаемое объявление упала
- Объявление сдано

---

## Критерии готовности

1. ✅ Kilo самостоятельно парсит все 4 сайта
2. ✅ Извлекает все поля из объявлений (в т.ч. из описания)
3. ✅ Переводит всё на русский язык
4. ✅ Записывает в Google Sheets через MCP
5. ✅ Дедуплицирует объявления
6. ✅ Отслеживает изменения цен и статусов
7. ✅ Заполняет лист `Аналитика` формулами и данными
8. ✅ Работает по расписанию
9. ✅ Всё работает без участия человека после первоначальной настройки

---

## Приоритеты

1. **P0**: halooglasi.com (самый простой, нет блокировок)
2. **P1**: oglasi.rs (относительно простой)
3. **P2**: imovina.net (средняя сложность)
4. **P3**: airbnb.ru (самый сложный, блокировки, нужен Playwright)

---

## Технологии

- **Язык**: Python 3.11+
- **Парсинг**: requests + BeautifulSoup4 / Playwright (для SPA)
- **MCP**: FastMCP (уже есть в проекте)
- **Google Sheets**: google-api-python-client через MCP
- **Перевод**: словари ключевых слов + возможен внешний API
- **Планирование**: schedule_wakeup (встроено в Kilo)

---

## Риски

1. **Блокировки**: airbnb.ru активно блочит → использовать Playwright + stealth
2. **Изменение структуры сайтов**: парсеры могут сломаться → мониторить логи
3. **Ограничения Google Sheets**: 10 млн ячеек → архивировать старые данные
4. **Качество данных**: не все поля будут извлекаемы → помечать как "не найдено"
