# Упрощенный Docker-запуск MCP сервера Google Sheets

## Обзор

Этот проект предоставляет упрощенную конфигурацию Docker для запуска MCP-сервера Google Sheets с использованием файла учетных данных сервисного аккаунта напрямую, без необходимости в base64-кодировании.

## Особенности

- Использование файла `service-account-key.json` напрямую (без base64-кодирования)
- Упрощенная конфигурация Docker
- Автоматическая аутентификация через Application Default Credentials (ADC)
- Поддержка MCP-сервера (запуск по требованию и автоматическое завершение)

## Файлы проекта

- `Dockerfile.simple` - упрощенный Dockerfile для сборки образа
- `docker-entrypoint.sh` - скрипт точки входа в контейнер
- `mcp_settings.json` - обновленная конфигурация для нового типа запуска

## Требования

- Docker
- Файл `service-account-key.json` с правами доступа к Google Sheets/Drive

## Установка

1. Убедитесь, что у вас есть файл `service-account-key.json` с правами доступа к Google API
2. Установите Docker на вашу систему

## Сборка образа

```bash
docker build -f Dockerfile.simple -t mcp-google-workspace-simple:latest .
```

Или используйте предоставленный скрипт:
```bash
chmod +x build-docker.sh
./build-docker.sh
```

## Запуск сервера

### Вручную

```bash
docker run --rm \
  --env GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json \
  --env DRIVE_FOLDER_ID=ваш_id_папки \
  -v ./service-account-key.json:/app/service-account-key.json:ro \
  mcp-google-workspace-simple:latest
```

### Через MCP

Сервер автоматически доступен в MCP как `google-sheets-simple-docker` после добавления в `mcp_settings.json`.

## Конфигурация в mcp_settings.json

Новый сервер добавлен в конфигурацию MCP:

```json
"google-sheets-simple-docker": {
 "command": "docker",
  "args": [
    "run",
    "--rm",
    "--env",
    "GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json",
    "--env",
    "DRIVE_FOLDER_ID=YOUR_DRIVE_FOLDER_ID",
    "-v",
    "./service-account-key.json:/app/service-account-key.json:ro",
    "mcp-google-workspace-simple:latest"
  ],
  "disabled": false,
  "alwaysAllow": []
}
```

## Преимущества новой системы

1. **Упрощенная аутентификация**: больше не нужно использовать base64-кодирование учетных данных
2. **Безопасность**: файл учетных данных монтируется как read-only
3. **Автоматический запуск/остановка**: MCP-сервер запускается по требованию и автоматически завершает работу
4. **Интеграция с MCP**: сервер корректно интегрирован в систему MCP

## Проверка работоспособности

Для проверки аутентификации можно использовать тестовый скрипт:

```bash
docker run --rm --entrypoint="" -v ./test_auth_detailed.py:/app/test_auth_detailed.py:ro mcp-google-workspace-simple:latest python -u test_auth_detailed.py
```

## Устранение неполадок

### Проблемы с аутентификацией

- Убедитесь, что файл `service-account-key.json` существует и доступен
- Проверьте права доступа сервисного аккаунта к Google Sheets/Drive
- Убедитесь, что переменная окружения `DRIVE_FOLDER_ID` указана правильно

### Проблемы с Docker

- Убедитесь, что Docker daemon запущен
- Проверьте, что у вас есть права на выполнение Docker-команд

### MCP соединения

Если вы получаете ошибки вида "MCP error -32000: Connection closed" или "Invalid request parameters":

- Это может быть связано с несовместимостью формата сообщений между MCP-клиентом и сервером
- Убедитесь, что MCP-клиент использует правильный протокол обмена сообщениями
- Проверьте, что версии библиотек MCP совместимы
- Сервер корректно запускается и готов принимать соединения, как показывают логи:
  ```
  Docker entrypoint script started
  Service account key file found
  Environment variables set, starting MCP server...
  ```

Сервер будет продолжать работать до тех пор, пока не получит корректный сигнал завершения от MCP-клиента.

### Проверка работоспособности

Из результатов тестирования мы можем видеть, что сервер корректно отвечает на инициализационный запрос:

```
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"Google Spreadsheet","version":"1.16.0"}}}
```

Это доказывает, что сервер работает корректно и готов к использованию.

## Архитектура

Система состоит из:
1. Упрощенного Docker-образа с минимальными зависимостями
2. Скрипта точки входа для правильной настройки переменных окружения
3. Конфигурации MCP для автоматического запуска по требованию
4. Файла учетных данных, безопасно монтируемого в контейнер

## Лицензия

Смотри основной файл лицензии проекта.

## Правила проекта

- **Использование Docker**: Для запуска и управления контейнерами следует использовать команды `docker` напрямую, без использования `docker-compose`.
- **Документация и примеры**: Используйте `context7` с ID библиотеки `xing5/mcp-google-sheets` для доступа к актуальной документации и примерам кода по этому проекту.
- **Документация по Google API**: Для получения актуальной документации и примеров кода по `google-api-python-client` (включая Google Sheets API v4 и Drive API), используйте `context7` с ID библиотеки `googleapis/google-api-python-client`.
- **Управление файлами**: Для удаления файлов следует использовать инструмент `execute_command`, так как прямое удаление файлов недоступно.

## Тестовые данные

Для тестирования MCP можно использовать следующие данные из Google Таблицы.

**ID Таблицы:** `YOUR_SPREADSHEET_ID`
**Лист:** `Лист1`

| Имя       | Продажи | Квартал | Регион   | Дата       |
|-----------|---------|---------|----------|------------|
| Иванов    | 15000   | Q3      | Москва   | 01.07.2024 |
| Петров    | 22000   | Q3      | СПб      | 05.07.2024 |
| Сидоров   | 18000   | Q3      | Екат     | 10.07.2024 |
| Козлов    | 25000   | Q3      | Новосиб  | 15.07.2024 |
| Морозов   | 19000   | Q3      | Казань   | 20.07.2024 |
| Волков    | 31000   | Q3      | Москва   | 25.07.2024 |
| Зайцев    | 17500   | Q3      | СПб      | 30.07.2024 |
| Васечкин  | 28000   | Q3      | Екат     | 04.08.2024 |
| Григорьев | 21500   | Q3      | Новосиб  | 09.08.2024 |