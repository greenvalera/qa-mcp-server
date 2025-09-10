# QA MCP - Конфігурація через .env файл

## ✅ Налаштування завершено!

Система тепер повністю читає конфігурацію з `.env` файлу, включаючи дані підключення до Confluence, спейс та сторінки для завантаження.

## 🔧 Конфігурація в .env файлі

```env
# Confluence Configuration
CONFLUENCE_BASE_URL=https://confluence.togethernetworks.com
CONFLUENCE_AUTH_TOKEN=your_personal_access_token_here
CONFLUENCE_SPACE_KEY=QMT
CONFLUENCE_ROOT_PAGES=117706559,43624449,340830206
```

### Опис параметрів:
- `CONFLUENCE_BASE_URL` - URL до Confluence інстансу (без `/wiki`)
- `CONFLUENCE_AUTH_TOKEN` - Personal Access Token для API
- `CONFLUENCE_SPACE_KEY` - Ключ спейсу (QMT = "QA Frontend Team")
- `CONFLUENCE_ROOT_PAGES` - Корньові сторінки через кому (Checklist MOB, Checklist WEB, Payment Page)

## 🚀 Використання

### 1. Зміна конфігурації
```bash
# Відредагуйте .env файл
nano .env

# Перезавантажте систему з новою конфігурацією
./scripts/reload_config.sh
```

### 2. Завантаження даних
```bash
# Автоматично використає конфігурацію з .env
./scripts/confluence/load_confluence_data.sh
```

### 3. Тестування підключення
```bash
# Перевірка підключення до Confluence
docker run --rm --network qa_mcp_qa_network --env-file .env \
  -e MYSQL_DSN=mysql+pymysql://qa:qa@qa_mysql:3306/qa \
  -e VECTORDB_URL=http://qa_qdrant:6333 \
  -v $(pwd)/scripts:/app/scripts \
  qa_mcp_loader python scripts/confluence/unified_loader.py --use-real-api --test-connection
```

## 📋 Виправлені проблеми

1. **✅ Хардкодинг в config.py**: Видалено значення за замовчуванням для `confluence_space_key` та `confluence_root_pages`
2. **✅ Валідація конфігурації**: Додана перевірка наявності обов'язкових змінних у `.env`
3. **✅ Автоматичне читання**: Система автоматично читає всі параметри з `.env` файлу
4. **✅ Інформативні повідомлення**: Показує поточну конфігурацію при запуску

## 🎯 Результат

Тепер система повністю динамічна і читає всі налаштування з `.env` файлу:

```
Using configuration from .env file:
  Space: QMT
  Root pages: 117706559,43624449,340830206
Confluence URL: https://confluence.togethernetworks.com
Auth token: ***set***
```

## 🔄 Workflow

1. **Редагування .env** → змінюєте параметри підключення
2. **reload_config.sh** → перезавантажує Docker контейнери
3. **load_confluence_data.sh** → завантажує дані з новими параметрами
4. **MCP сервер** → готовий до використання з новими даними

Система готова для використання в Cursor IDE!
