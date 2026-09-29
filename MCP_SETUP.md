# Google Sheets MCP — подробная инструкция по настройке

## 1. Что это

Google Sheets MCP — удалённый сервер протокола контекста модели (MCP), который позволяет ИИ-агентам безопасно читать и изменять данные в Google Таблицах. После настройки Kilo сможет напрямую писать парсерные данные в таблицу, читать объявления, обновлять цены и статусы.

## 2. Предварительные требования

### 2.1 Участие в программе предварительного просмотра Google Workspace для разработчиков

Сервер Google Sheets MCP находится в рамках программы предварительного просмотра. Убедиться, что ваш аккаунт Google включён в эту программу:
- Перейти на https://developers.google.com/workspace/preview
- Нажать «Запросить доступ» или «Join the preview»
- Дождаться подтверждения на почте

### 2.2 Google Cloud CLI (gcloud)

Установить Google Cloud CLI:
- Скачать с https://cloud.google.com/sdk/docs/install
- При установке выбрать проект, или создать новый
- Обновить компоненты:

```bash
gcloud components update
```

### 2.3 Проект Google Cloud

Если проекта ещё нет:
1. Открыть https://console.cloud.google.com/
2. Нажать «Select a project» → «New Project»
3. Ввести название, например `apartments-belgrade`
4. Сохранить `PROJECT_ID` (например `apartments-belgrade-123456`)

## 3. Включить API в проекте

В терминале выполнить:

```bash
gcloud services enable sheets.googleapis.com --project=PROJECT_ID
gcloud services enable sheetsmcp.googleapis.com --project=PROJECT_ID
```

Где `PROJECT_ID` — идентификатор вашего проекта в Google Cloud.

Проверить, что сервисы включены:

```bash
gcloud services list --enabled --project=PROJECT_ID
```

В выводе должны быть:
- `sheets.googleapis.com` — Google Таблицы API
- `sheetsmcp.googleapis.com` — Google Sheets MCP API

## 4. Настроить экран согласия OAuth

### 4.1 Открыть раздел брендинга

1. Открыть https://console.cloud.google.com/auth/branding?project=PROJECT_ID
2. Если появится сообщение «Платформа аутентификации Google ещё не настроена» — нажать «Начать»

### 4.2 Информация о приложении

- **Название приложения**: `Sheets MCP Server`
- **Электронная почта службы поддержки пользователей**: выбрать свой адрес Gmail или группу
- Нажать «Далее»

### 4.3 Аудитория

- Выбрать **Внутренняя** (Internal), если аккаунт Google Workspace организации
- Или **Внешняя** (External), если личный аккаунт Gmail
  - При выборе «Внешняя» позже потребуется добавить тестовых пользователей
- Нажать «Далее»

### 4.4 Контактная информация

- Ввести email, на который будут приходить уведомления об изменениях проекта
- Нажать «Далее»

### 4.5 Завершение

- Прочитать «Политику использования пользовательских данных сервисов Google API»
- Поставить галочку «Я согласен...»
- Нажать «Продолжить»
- Нажать «Создать»

### 4.6 Если выбрали «Внешняя» аудитория — добавить тестовых пользователей

1. В меню слева: «Аудитория»
2. «Проверка пользователей» → «Добавить пользователей»
3. Ввести свой email и других авторизованных пользователей
4. «Сохранить»

### 4.7 Добавить области доступа (scopes)

1. В меню слева: «Доступ к данным»
2. «Добавить или удалить области действия»
3. В разделе «Добавить области действия вручную» вставить:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/spreadsheets.readonly`
   - `https://www.googleapis.com/auth/spreadsheets`
4. Нажать «Добавить в таблицу»
5. «Обновить»
6. «Сохранить»

## 5. Создать OAuth 2.0 клиента

### 5.1 Открыть Credentials

1. Перейти в Google Cloud Console → «APIs & Services» → «Credentials»
   https://console.cloud.google.com/apis/credentials?project=PROJECT_ID
2. Нажать «+ CREATE CREDENTIALS» → «OAuth client ID»

### 5.2 Настроить клиент

- **Тип приложения**: выбрать «Веб-приложение» (Web application)
- **Имя**: ввести любое, например `Kilo Sheets MCP Client`
- **Authorized redirect URIs**: нажать «+ ADD URI» и вставить:
  ```
  https://antigravity.google/oauth-callback
  ```
- Нажать «Create»

### 5.3 Сохранить данные

После создания появится окно с данными клиента. **Скопировать и сохранить**:
- **Client ID** (например `123456789-abc.apps.googleusercontent.com`)
- **Client Secret** (например `GOCSPX-xxxxxxxxxxxx`)

> Важно: Client Secret храните в секрете. Не коммитьте его в репозиторий.

## 6. Настроить Kilo для работы с MCP

### 6.1 Найти конфигурационный файл Kilo

Конфигурация Kilo ищется в следующих местах (по приоритету):
1. `.kilo/` в рабочей директории проекта
2. Глобальная директория: `C:\Users\maria\.config\kilo\`
3. Файл `kilo.json` в корне рабочей директории

### 6.2 Добавить конфигурацию MCP

Открыть конфигурационный файл Kilo (например `kilo.json` или `mcp_config.json` в папке `.kilo/`) и добавить секцию:

```json
{
  "mcpServers": {
    "sheets": {
      "serverUrl": "https://sheetsmcp.googleapis.com/mcp/v1",
      "oauth": {
        "clientId": "СКОПИРОВАННЫЙ_CLIENT_ID",
        "clientSecret": "СКОПИРОВАННЫЙ_CLIENT_SECRET"
      }
    }
  }
}
```

### 6.3 Пример полного конфига `kilo.json`

```json
{
  "mcpServers": {
    "sheets": {
      "serverUrl": "https://sheetsmcp.googleapis.com/mcp/v1",
      "oauth": {
        "clientId": "123456789-abc.apps.googleusercontent.com",
        "clientSecret": "GOCSPX-xxxxxxxxxxxx"
      }
    }
  },
  "permissions": {
    "allow": ["bash:read", "edit", "write", "read", "grep", "glob"]
  }
}
```

### 6.4 Перезапустить Kilo

После изменения конфигурации перезапустить Kilo, чтобы он подхватил новый MCP сервер.

## 7. Аутентификация

### 7.1 Запустить панель управления MCP в Kilo

В терминале Kilo выполнить команду:

```
/mcp
```

### 7.2 Выбрать сервер sheets

В интерактивной панели TUI:
1. Клавишами со стрелками выбрать `sheets`
2. Перейти к действию «Authenticate» / «Аутентификация»
3. Нажать Enter

### 7.3 Пройти OAuth в браузере

1. Откроется браузер с страницей входа Google
2. Войти в аккаунт Google, который был добавлен как тестовый пользователь (если External)
3. Нажать «Continue» / «Продолжить»
4. Скопировать код авторизации из браузера
5. Вернуться в терминал Kilo, вставить код, нажать Enter

### 7.4 Проверить статус

В панели `/mcp` проверённые и аутентифицированные серверы отображаются с пометкой «Authenticated» рядом с именем.

## 8. Создать Google Таблицу

### 8.1 Создать таблицу

1. Открыть https://sheets.google.com
2. «Создать» → «Пустая таблица»
3. Верхнее меню → «Файл» → «Сохранить»
4. Ввести название, например `Квартиры Белград`
5. Скопировать ID таблицы из URL:
   - URL вида: `https://docs.google.com/spreadsheets/d/1AbCDeFGhIjKlMnOpQrStUvWxYz1234567890/edit#gid=0`
   - ID: `1AbCDeFGhIjKlMnOpQrStUvWxYz1234567890`

### 8.2 Создать листы

Создать 4 листа (вкладки внизу):

1. `Объявления` — основной лист с данными
2. `Аналитика` — общие метрики
3. `Чек-лист_осмотра` — осмотры
4. `Архив` — закрытые объекты

### 8.3 Заполнить заголовки

В листе `Объявления` в первой строке (A1:AP1) вставить заголовки согласно разделу 4 документа VISION.md.

Рекомендуемый порядок заголовков:
```
ID_объявления | Площадка | Ссылка | Дата_первого_появления | Дата_нашли | Дата_последнего_обновления | Дата_сдачи | Дней_на_рынке | Район | Адрес | Тип_жилья | Комнат | Кухня | Площадь_м2 | Этаж | Цена_аренды_EUR | Валюта | Коммуналка_EUR | Электричество_включено | Залог_EUR | Залог_возвращается | Другие_платежи | Итоговая_стоимость_EUR | Оплата_за_3_недели | Мин_срок_аренды_мес | Собака_разрешена | Кошка_разрешена | Доплата_за_животных_EUR | Холодильник | Плита | Духовка | Стиральная_машина | Посудомоечная_машина | Горячая_вода | Wi_Fi | Мебель_кровати | Мебель_общая | Цена_сейчас_EUR | Изменение_цены_EUR | Статус | Частота_появления_в_день | Примечания
```

## 9. Проверить работу MCP

### 9.1 Тест 1: прочитать лист

В Kilo выполнить запрос:

```
Прочитай лист `Объявления` из таблицы `1AbCDeFGhIjKlMnOpQrStUvWxYz1234567890`
```

Ожидаемый результат: массив значений с заголовками и данными (если есть).

### 9.2 Тест 2: записать строку

Попробовать добавить тестовую строку через `update_values`.

### 9.3 Проверить доступ

Если получаете ошибку 403 или 404:
- Проверить, что таблица доступна по ссылке «Все, у кого есть ссылка» → «Редактор»
- Проверить, что OAuth scopes добавлены корректно
- Проверить, что Client ID и Client Secret в конфиге верные

## 10. Типичные проблемы и решения

### 10.1 Ошибка: «Access blocked: This app's request is invalid»

Причина: неправильный redirect URI в OAuth клиенте.

Решение:
- Проверить, что в OAuth клиенте добавлен `https://antigravity.google/oauth-callback`
- Убедиться, что нет лишних пробелов

### 10.2 Ошибка: «Access blocked: Authorization Error»

Причина: пользователь не добавлен в тестовые (для External типа).

Решение:
- Добавить свой email в «Аудитория» → «Проверка пользователей»
- Или переключить на «Внутренняя» аудиторию

### 10.3 Ошибка: «Request had insufficient authentication scopes»

Причина: не добавлены нужные scopes в OAuth consent screen.

Решение:
- Перейти в «Доступ к данным» → «Добавить или удалить области действия»
- Добавить все 4 scopes из раздела 4.7
- Нажать «Обновить» и «Сохранить»
- Повторить аутентификацию в Kilo

### 10.4 Ошибка: «The caller does not have permission»

Причина: нет доступа к таблице.

Решение:
- Открыть таблицу в браузере
- «Настройка доступа» → добавить аккаунт Google как «Редактор»
- Или сделать таблицу доступной по ссылке

### 10.5 Ошибка: «sheetsmcp.googleapis.com is not enabled»

Причина: API не включён в проекте.

Решение:
```bash
gcloud services enable sheets.googleapis.com --project=PROJECT_ID
gcloud services enable sheetsmcp.googleapis.com --project=PROJECT_ID
```

## 11. Ссылки

- Документация Google Sheets API: https://developers.google.com/workspace/sheets/api/reference/rest?hl=ru
- Настройка MCP (Google): https://developers.google.com/workspace/sheets/api/guides/configure-mcp-server?hl=ru
- Программа предварительного просмотра: https://developers.google.com/workspace/preview
- Google Cloud Console: https://console.cloud.google.com/
