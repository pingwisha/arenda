-+693# Google Sheets MCP Server

MCP (Model Context Protocol) сервер для взаимодействия с Google Sheets, Google Docs и Google Drive.

## Возможности

### Google Sheets
- Чтение данных из таблиц
- Обновление ячеек
- Пакетное обновление нескольких диапазонов
- Добавление строк и столбцов
- Создание, переименование, копирование и удаление листов
- Получение формул из ячелей
- Получение списка таблиц из Google Drive

### Google Docs
- Чтение содержимого документов
- Извлечение текста из документов
- Вставка текста в документы
- Удаление текста из документов
- Создание документов (опционально)

### Google Drive
- Поиск файлов
- Скачивание Google Docs как TXT
- Обновление содержимого файлов
- Предоставление доступа к таблицам

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/mcp-google-sheets.git
cd mcp-google-sheets

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

## Настройка аутентификации

### Способ 1: Service Account (рекомендуется)

1. Создайте сервисный аккаунт в [Google Cloud Console](https://console.cloud.google.com/)
2. Скачайте JSON-файл с ключом
3. Предоставьте сервисному аккаунту доступ к таблицам и диску

Укажите путь к файлу:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Способ 2: OAuth 2.0

1. Создайте OAuth credentials в [Google Cloud Console](https://console.cloud.google.com/)
2. Скачайте `credentials.json`
3. При первом запуске будет предложено авторизоваться через браузер
4. Токен будет сохранён в `token.json`

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Путь к файлу сервисного аккаунта | `service-account-key.json` |
| `CREDENTIALS_CONFIG` | Base64-encoded JSON сервисного аккаунта | - |
| `DRIVE_FOLDER_ID` | ID папки в Google Drive для поиска таблиц | - |
| `ENABLE_CREATE_TOOLS` | Включить инструменты создания (`true`/`false`) | `false` |

## Запуск

```bash
python server.py
```

## Использование с MCP-клиентами

### Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-sheets": {
      "command": "python",
      "args": ["/path/to/mcp-google-sheets/server.py"]
    }
  }
}
```

## Инструменты

| Инструмент | Описание |
|------------|----------|
| `get_sheet_data` | Получить данные из листа |
| `get_sheet_formulas` | Получить формулы из ячеек |
| `update_cells` | Обновить значения ячеек |
| `batch_update_cells` | Пакетное обновление нескольких диапазонов |
| `add_rows` | Добавить строки |
| `add_columns` | Добавить столбцы |
| `list_sheets` | Получить список листов |
| `copy_sheet` | Копировать лист |
| `rename_sheet` | Переименовать лист |
| `delete_sheet` | Удалить лист |
| `list_spreadsheets` | Получить список таблиц |
| `share_spreadsheet` | Предоставить доступ к таблице |
| `get_doc_content` | Получить содержимое документа |
| `get_doc_text` | Получить текст документа |
| `search_drive_files` | Поиск файлов в Drive |

## Лицензия

MIT