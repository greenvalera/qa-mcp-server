# MCP QA Search Server

MCP (Model Context Protocol) сервер для релевантного пошуку по документах з Confluence з автоматичною класифікацією за фічами.

## Архітектура

- **MCP Server**: JSON-RPC сервер з підтримкою HTTP та stdio
- **Confluence Loader**: CLI скрипт для імпорту сторінок з Confluence
- **Vector DB**: Qdrant для зберігання векторних представлень чанків
- **MySQL**: Метадані документів та фіч
- **OpenAI**: Embeddings та AI feature tagging

## MVP v.0.1 Features ✅

- ✅ MCP сервер з 4 інструментами (qa.search, qa.list_features, qa.docs_by_feature, qa.health)
- ✅ **НОВИНКА**: Офіційний Python MCP SDK (FastMCP) замість кастомної реалізації
- ✅ JSON-RPC підтримка через HTTP та stdio
- ✅ HTTP REST API (зворотна сумісність)
- ✅ OpenAI integration (embeddings + LLM для feature tagging)
- ✅ Qdrant векторна база даних
- ✅ MySQL для метаданих
- ✅ Confluence loader з мок API
- ✅ Docker containers та docker-compose
- ✅ Автоматична класифікація документів за фічами
- ✅ Базові тести

## Міграція на FastMCP 2.12.2 v.0.2 ✅

Проект було переписано з використанням актуальної версії [FastMCP 2.12.2](https://github.com/jlowin/fastmcp):

- **FastMCP 2.12.2**: Використання найновішої версії "The fast, Pythonic way to build MCP servers"
- **Новий MCP сервер**: `app/mcp_server.py` з використанням `FastMCP` та `Context`
- **Context API**: Підтримка контекстного логування та розширених функцій MCP
- **Новий лончер**: `mcp_server.py` для підключення до Cursor
- **Зворотна сумісність**: старий HTTP сервер залишається доступним
- **Спрощена архітектура**: менше коду, більша надійність
- **Офіційна підтримка**: використання стандартного MCP протоколу

## Швидкий старт

### 1. Налаштування змінних оточення

```bash
cp env.example .env
# Відредагуйте .env з вашим OPENAI_API_KEY
```

### 2. Запуск через Docker

```bash
# Встановіть OPENAI_API_KEY в .env файлі
export OPENAI_API_KEY=your_key_here

# Запустіть сервіси
docker compose up -d

# Перевірте статус
docker compose ps
```

### 3. Завантаження тестових даних

```bash
# Використовує мок Confluence API з тестовими документами
python scripts/confluence_loader.py --spaces QA,ENG --labels checklist --once
```

### 4. Підключення до Cursor IDE

#### 4.1. Налаштування MCP в Cursor

Додайте конфігурацію в файл `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "qa-search": {
      "command": "python3",
      "args": ["/path/to/your/project/qa_mcp/mcp_server.py"]
    }
  }
}
```

**Важливо:** Замініть `/path/to/your/project/` на реальний шлях до вашого проекту.

**Новий MCP сервер**: Проект було переписано з використанням офіційного Python MCP SDK (FastMCP). Новий сервер використовує `mcp_server.py` замість `mcp_local.py`.

#### 4.2. Перезапуск Cursor

Після додавання конфігурації:
1. Повністю закрийте Cursor
2. Запустіть Cursor знову
3. Перевірте в Settings → MCP Tools що з'явився `qa-search` сервер

#### 4.3. Альтернативні способи підключення

**Через HTTP (не рекомендується для production):**
```json
{
  "mcpServers": {
    "qa-search": {
      "url": "http://localhost:3000/jsonrpc",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```

**Через Docker (якщо у вас проблеми з локальним Python):**
```json
{
  "mcpServers": {
    "qa-search": {
      "command": "docker",
      "args": ["exec", "-i", "qa_mcp_server", "python", "-m", "app.mcp_server"]
    }
  }
}
```

#### 4.4. Використання в чаті

Тепер ви можете використовувати MCP інструменти в чаті Cursor:
- `qa_health` - перевірка стану системи
- `qa_search` - пошук документів
- `qa_list_features` - список функцій
- `qa_docs_by_feature` - документи за функцією

**Приклади використання в Cursor:**
```
Використай qa_health інструмент для перевірки стану системи

Знайди документи про authentication за допомогою qa_search

Покажи всі доступні фічі через qa_list_features з лімітом 5
```

### 5. Тестування MCP інструментів

```bash
# Локальний тест нового MCP сервера
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "qa_health", "arguments": {}}, "id": 1}' | python3 mcp_server.py

# HTTP сервер видалено - використовуйте тільки FastMCP
# curl -X GET http://localhost:3000/health - НЕ ПРАЦЮЄ

# Тест FastMCP сервера через Docker
docker run --rm -i --network qa_mcp_qa_network qa_mcp-mcp-server python -m app.mcp_server
```

## MCP Інструменти

### `qa_search` (в Cursor) / `qa.search` (в HTTP API)
Релевантний пошук по документах/чанках із підтримкою фільтрів.

**Параметри:**
- `query` (required) - пошуковий запит
- `top_k` - кількість результатів (default: 10, max: 50)
- `feature_names` - фільтр по назвах фіч
- `space_keys` - фільтр по просторам Confluence
- `filters` - додаткові фільтри
- `return_chunks` - повертати інформацію про чанки (default: true)

### `qa_list_features` (в Cursor) / `qa.list_features` (в HTTP API)
Список фіч з описами та переліком пов'язаних документів.

**Параметри:**
- `with_documents` - включити назви документів (default: true)
- `limit` - максимум фіч (default: 100, max: 500)
- `offset` - пропустити фічі (default: 0)

### `qa_docs_by_feature` (в Cursor) / `qa.docs_by_feature` (в HTTP API)
Документи для заданої фічі.

**Параметри:**
- `feature_name` OR `feature_id` - ідентифікатор фічі
- `limit` - максимум документів (default: 50, max: 200)
- `offset` - пропустити документи (default: 0)

### `qa_health` (в Cursor) / `qa.health` (в HTTP API)
Перевірка стану баз даних та сервісів.

**Параметри:** немає

**Примітка:** В Cursor використовуйте назви з підкресленнями (`qa_health`), а в прямих HTTP викликах - з крапками (`qa.health`).

## HTTP API

### REST Endpoints
- `GET /health` - health check
- `POST /search` - пошук документів
- `GET /features` - список фіч
- `GET /features/{id_or_name}/documents` - документи фічі
- `GET /tools` - список MCP інструментів

### JSON-RPC Endpoint
- `POST /jsonrpc` - виклик MCP інструментів через JSON-RPC

**Приклад запиту:**
```json
{
  "jsonrpc": "2.0",
  "method": "qa.search",
  "params": {
    "query": "authentication testing",
    "top_k": 5
  },
  "id": 1
}
```

## Розробка

### Локальна розробка

```bash
# Встановлення залежностей
pip install -r app/requirements.txt

# Запуск тестів
pytest tests/

# Запуск FastMCP 2.12.2 сервера (stdio режим)
python3 mcp_server.py

# Альтернативно через модуль
python -m app.mcp_server

# HTTP сервер видалено - використовуйте тільки FastMCP
```

### Завантаження даних

```bash
# З мок Confluence API (за замовчуванням)
python scripts/confluence_loader.py --spaces QA,ENG --labels checklist --once

# Допоможні опції
python scripts/confluence_loader.py --help
```

## Конфігурація

### Основні змінні оточення

**Обов'язкові:**
- `OPENAI_API_KEY` - ключ OpenAI API

**Необов'язкові:**
- `OPENAI_MODEL` - модель LLM (default: gpt-4o-mini)
- `OPENAI_EMBEDDING_MODEL` - модель embeddings (default: text-embedding-3-small)
- `MYSQL_DSN` - підключення до MySQL (default: локальний контейнер)
- `VECTORDB_URL` - URL Qdrant (default: http://localhost:6333)
- `APP_PORT` - порт HTTP сервера (default: 3000)
- `MAX_TOP_K` - максимум результатів пошуку (default: 50)
- `CHUNK_SIZE` - розмір чанка в токенах (default: 800)
- `CHUNK_OVERLAP` - перетин чанків в токенах (default: 200)
- `FEATURE_SIM_THRESHOLD` - поріг схожості для фіч (default: 0.80)

### Підключення до зовнішніх БД

Для використання віддалених баз даних змініть змінні:

```bash
# PostgreSQL замість MySQL
MYSQL_DSN=postgresql://user:password@host:5432/database

# Віддалений Qdrant
VECTORDB_URL=http://your-qdrant-host:6333

# Для production
ENVIRONMENT=production
```

## Структура проекту

```
qa_mcp/
├── app/                    # Основний додаток
│   ├── ai/                # OpenAI модулі
│   ├── data/              # Репозиторії БД
│   ├── models/            # Моделі даних
│   ├── mcp_tools/         # MCP інструменти
│   └── server.py          # Головний сервер
├── scripts/               # CLI скрипти
│   ├── confluence_loader.py
│   ├── confluence_mock.py
│   └── test_mcp_client.py
├── tests/                 # Тести
├── docker-compose.yml     # Docker конфігурація
├── Dockerfile
└── README.md
```

## Приклади використання

### Пошук документів

```bash
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication testing procedures",
    "top_k": 3,
    "feature_names": ["Authentication", "Testing"]
  }'
```

### JSON-RPC виклик

```bash
curl -X POST http://localhost:3000/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "qa.list_features",
    "params": {"limit": 5},
    "id": 1
  }'
```

### Stdio режим для MCP клієнтів

```bash
echo '{"jsonrpc":"2.0","method":"qa.health","id":1}' | python -m app.server --stdio
```

## Troubleshooting

### Перевірка статусу
```bash
# Health check
curl http://localhost:3000/health

# Docker logs
docker compose logs mcp-server
docker compose logs mysql
docker compose logs qdrant
```

### MCP підключення до Cursor

#### Перевірка конфігурації
```bash
# Перевірте що файл конфігурації існує
cat ~/.cursor/mcp.json

# Перевірте що шлях до скрипта правильний
ls -la /path/to/your/project/qa_mcp/mcp_local.py

# Тест MCP скрипта
python3 /path/to/your/project/qa_mcp/mcp_local.py
```

#### Діагностика проблем MCP
```bash
# Тест tools/list (новий MCP сервер)
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | python3 mcp_server.py

# Тест конкретного інструменту (новий MCP сервер)
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "qa_health", "arguments": {}}, "id": 1}' | python3 mcp_server.py

# Старий launcher видалено - тепер використовуйте тільки FastMCP
# python3 mcp_local.py - ФАЙЛ ВИДАЛЕНО
```

#### Типові помилки MCP

1. **"Failed to call Docker server: HTTP Error 404"**
   - Перевірте що Docker контейнери запущені: `docker compose ps`
   - Перевірте що порт 3000 доступний: `curl http://localhost:3000/health`

2. **"Loading Tools" або "No tools or prompts"**
   - Перезапустіть Cursor повністю
   - Перевірте що шлях в `mcp.json` правильний
   - Перевірте що `python3` доступний в PATH

3. **"Method not found: qa_health"**
   - Перевірте що Docker контейнери запущені
   - Перевірте що інструменти викликаються як `qa_health`, а не `qa.health`

### Типові проблеми

1. **OpenAI API помилки** - перевірте OPENAI_API_KEY
2. **База даних не доступна** - перевірте docker compose ps
3. **Порт зайнятий** - змініте APP_PORT в .env
4. **Немає даних для пошуку** - запустіть confluence_loader.py

## Подальші етапи (v0.2+)

- Гібридний пошук (vector + BM25)
- Крос-енкодер переранжування
- Реальний Confluence API
- UI дашборд адміністрування
- Метрики та моніторинг
- Покращена безпека
