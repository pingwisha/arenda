# MCP Quick Start — минимум действий

## Что уже сделано

- Локальный MCP-сервер Google Workspace готов в папке `kilocode-mcp-google-workspace/`
- Виртуальное окружение `venv` уже создано
- Конфиг `mcp_settings.json` уже настроен на запуск локального сервера

## Что нужно сделать вам (4 шага)

### Шаг 1. Создать Service Account в Google Cloud

1. Открыть https://console.cloud.google.com/iam-admin/serviceaccounts?project=YOUR_PROJECT_ID
2. Нажать «+ CREATE SERVICE ACCOUNT»
3. Имя: `apartments-parser`
4. Нажать «CREATE AND CONTINUE»
5. Роль: `Editor` (или `Editor` в Drive и Sheets)
6. «DONE»

### Шаг 2. Скачать JSON-ключ

1. Открыть созданный сервисный аккаунт
2. Вкладка «KEYS» → «ADD KEY» → «Create new key»
3. Тип: `JSON` → «CREATE»
4. Файл скачается автоматически

### Шаг 3. Положить ключ в проект

Переименовать скачанный файл в `service-account-key.json` и положить в папку:

```
C:\Users\maria\OneDrive\Документы\квартиры\kilocode-mcp-google-workspace\service-account-key.json
```

### Шаг 4. Дать доступ сервисного аккаунта к Google Таблице

1. Открыть вашу Google Таблицу
2. «Настройка доступа» (Share)
3. Вставить email сервисного аккаунта из JSON-файла (поле `client_email`)
4. Права: `Редактор`
5. «Отправить»

## Проверка

После этого перезапустить Kilo. MCP-сервер `google-sheets-py` должен появиться в списке доступных инструментов.

Проверить можно командой:

```
Прочитай лист `Объявления` из таблицы `ID_ВАШЕЙ_ТАБЛИЦЫ`
```

## Если что-то пошло не так

- Убедиться, что `service-account-key.json` лежит именно в `kilocode-mcp-google-workspace/`
- Убедиться, что сервисный аккаунт добавлен в доступы к таблице
- Перезапустить Kilo после добавления файла
