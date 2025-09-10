# Confluence Integration Module

Цей модуль забезпечує інтеграцію з Atlassian Confluence для імпорту документації в QA MCP систему.

## ⚠️ ВАЖЛИВЕ ПОПЕРЕДЖЕННЯ

**Mock API додає фейкові тестові дані в вашу production базу даних!**

- ✅ **Безпечно**: `--use-real-api` - працює з реальним Confluence
- ❌ **НЕБЕЗПЕЧНО**: Без флагу `--use-real-api` - додає тестові дані

**Завжди перевіряйте, який API використовується перед запуском!**

## 📁 Структура модуля

```
scripts/confluence/
├── __init__.py                 # Пакет для імпорту модулів
├── confluence_loader.py        # Головний оркестратор завантаження
├── confluence_mock.py          # Mock API для тестування та розробки
├── confluence_real.py          # Реальний Confluence API клієнт
├── load_confluence_data.sh     # Shell скрипт для завантаження даних
└── README.md                   # Ця документація
```

## 🔧 Компоненти

### 1. `unified_loader.py` - **ОСНОВНИЙ ЗАВАНТАЖУВАЧ** ⭐

**Призначення**: Об'єднаний завантажувач для MySQL та векторної бази даних.

**Основні функції**:
- Завантаження сторінок з Confluence (через mock або реальний API)
- **MySQL**: Створення структурованих QA об'єктів (QASection, Checklist, TestCase, Config)
- **Vector DB**: Розбиття тексту на чанки, генерація embeddings, збереження в Qdrant
- AI аналіз контенту через QAContentAnalyzer
- Детальний моніторинг прогресу та статистика
- Підтримка часткового завантаження (тільки MySQL або тільки Vector DB)

### 2. `confluence_loader.py` - Застарілий завантажувач

**Призначення**: Старий завантажувач тільки для векторної бази (застарілий).

**⚠️ УВАГА**: Використовуйте `unified_loader.py` замість цього файлу!

**Використання**:
```bash
# ⭐ РЕКОМЕНДОВАНИЙ СПОСІБ - Об'єднане завантаження
python3 scripts/confluence/unified_loader.py --use-real-api --use-config

# Завантаження з mock API (для тестування)
python3 scripts/confluence/unified_loader.py --limit 5

# Тільки MySQL (без векторної бази)
python3 scripts/confluence/unified_loader.py --use-real-api --use-config --mysql-only

# Тільки векторна база (без MySQL)
python3 scripts/confluence/unified_loader.py --use-real-api --use-config --vector-only

# Тестування з'єднання
python3 scripts/confluence/unified_loader.py --use-real-api --test-connection
```

**Параметри командного рядка**:
- `--page-ids` - Список root page IDs (через кому)
- `--spaces` - Список просторів Confluence (через кому)
- `--labels` - Фільтр по лейблах
- `--since` - Завантажити документи, оновлені після дати (ISO формат)
- `--limit` - Максимальна кількість чеклістів для обробки
- `--use-config` - Використовувати page IDs з конфігурації (.env)
- `--use-real-api` - Використовувати реальний Confluence API
- `--test-connection` - Тестувати з'єднання з Confluence
- `--mysql-only` - Завантажити тільки в MySQL (пропустити векторну базу)
- `--vector-only` - Завантажити тільки в векторну базу (пропустити MySQL)

### 2. `confluence_mock.py` - Mock API

**Призначення**: Симуляція Confluence API для розробки та тестування без налаштування реального Confluence.

**Особливості**:
- Генерує фейкові дані для тестування
- Імітує API відповіді без реального підключення
- Дозволяє розробляти без налаштування Confluence
- Включає приклади QA чеклістів, API документації, архітектурних документів

**Використовується автоматично** коли `--use-real-api` не вказано.

### 3. `confluence_real.py` - Реальний Confluence API

**Призначення**: Клієнт для роботи з реальним Confluence API через atlassian-python-api.

**Функції**:
- Підключення до реального Confluence
- Отримання сторінок, просторів, лейблів
- Нормалізація Confluence storage format до plain text
- Обробка HTML та макросів Confluence
- Тестування з'єднання

**Вимоги**:
- Налаштований `.env` файл з Confluence credentials
- Встановлений `atlassian-python-api` пакет

### 4. `load_confluence_data.sh` - Shell скрипт

**Призначення**: Зручний спосіб завантаження даних з використанням конфігурації з `.env` файлу.

**Функції**:
- Перевіряє наявність `.env` файлу
- Відображає поточну конфігурацію
- Валідує необхідні змінні середовища
- Запускає confluence_loader з правильними параметрами

**Використання**:
```bash
# З кореневої директорії проекту
./scripts/confluence/load_confluence_data.sh
```

## ⚙️ Конфігурація

### Змінні середовища (.env файл)

```bash
# Confluence налаштування
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_AUTH_TOKEN=your_auth_token
CONFLUENCE_SPACE_KEY=QA
CONFLUENCE_ROOT_PAGES=123456789,987654321

# OpenAI налаштування
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Vector DB налаштування
VECTORDB_URL=http://localhost:6333
```

### Отримання Confluence Auth Token

1. Перейдіть в [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Створіть новий API token
3. Додайте його в `.env` файл як `CONFLUENCE_AUTH_TOKEN`

## 🚀 Швидкий старт

### 1. Тестування з Mock API

⚠️ **ВАЖЛИВО**: Mock API додає фейкові тестові дані в вашу векторну базу даних!

```bash
# Активація віртуального середовища
source venv/bin/activate

# Завантаження тестових даних (ДОДАЄ ФЕЙКОВІ ДАНІ!)
python3 -m scripts.confluence.confluence_loader --once
```

**Увага**: Ця команда додасть 6 тестових документів в Qdrant. Для видалення тестових даних використовуйте:

```bash
# Видалення тестових документів з Qdrant
curl -X POST "http://localhost:6333/collections/qa_chunks/points/delete" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"must": [{"key": "confluence_page_id", "match": {"any": ["123456789", "123456790", "123456791", "234567890", "234567891", "345678901"]}}]}}'
```

### 2. Робота з реальним Confluence

```bash
# Налаштування .env файлу
cp env.example .env
# Відредагуйте .env з вашими Confluence credentials

# Тестування з'єднання
python3 scripts/confluence/unified_loader.py --use-real-api --test-connection

# Завантаження даних (ЗАВЖДИ використовуйте --use-real-api!)
./scripts/confluence/load_confluence_data.sh
```

⚠️ **ВАЖЛИВО**: Завжди використовуйте флаг `--use-real-api` для роботи з реальними даними!

### 3. Завантаження конкретних даних

```bash
# Завантаження конкретних просторів
python3 scripts/confluence/unified_loader.py \
  --use-real-api \
  --spaces "QA,ENG,DOC"

# Завантаження конкретних сторінок з дочірніми
python3 scripts/confluence/unified_loader.py \
  --use-real-api \
  --page-ids "123456789,987654321"

# Завантаження документів, оновлених за останній тиждень
python3 scripts/confluence/unified_loader.py \
  --use-real-api \
  --since "2024-01-01T00:00:00"

# Завантаження з лімітом для тестування
python3 scripts/confluence/unified_loader.py \
  --use-real-api \
  --use-config \
  --limit 10
```

## 📊 Процес завантаження

### MySQL (структуровані QA дані):
1. **Отримання сторінок** - Завантаження з Confluence API або mock
2. **AI аналіз контенту** - QAContentAnalyzer аналізує контент
3. **Створення QA об'єктів** - QASection, Checklist, TestCase, Config
4. **Збереження в MySQL** - Структуровані дані для QA менеджменту

### Vector DB (векторний пошук):
1. **Нормалізація контенту** - Видалення HTML, макросів, форматування
2. **Chunking** - Розбиття тексту на частини з перекриттям
3. **Embeddings** - Генерація векторних представлень через OpenAI
4. **Збереження в Qdrant** - Векторна база для AI-пошуку

## 🔍 Моніторинг та логування

### Перевірка стану бази даних

```bash
# Загальна статистика
curl -X GET "http://localhost:6333/collections/qa_chunks" | jq '.result.points_count'

# Перевірка наявності тестових даних
curl -X POST "http://localhost:6333/collections/qa_chunks/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "confluence_page_id",
          "match": {
            "any": ["123456789", "123456790", "123456791", "234567890", "234567891", "345678901"]
          }
        }
      ]
    },
    "limit": 10
  }' | jq '.result.points | length'
# Має повернути 0 для чистої бази

# Перевірка останніх документів
curl -X POST "http://localhost:6333/collections/qa_chunks/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": true}' | jq '.result.points[] | {title: .payload.title, space: .payload.space, page_id: .payload.confluence_page_id}'
```

### Логування процесу

Скрипт надає детальну інформацію про процес:
- Кількість знайдених сторінок
- Прогрес обробки кожної сторінки
- Кількість створених чанків
- Помилки та попередження

## 🛠️ Розробка та тестування

### ⚠️ Безпека даних та тестування

**КРИТИЧНО ВАЖЛИВО**: Mock API додає фейкові дані в production базу даних!

#### Безпечне тестування

1. **Використовуйте окрему тестову базу**:
```bash
# Створіть окрему колекцію для тестів
curl -X PUT "http://localhost:6333/collections/qa_chunks_test" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
```

2. **Тестуйте імпорти без збереження**:
```bash
# Тест без збереження в базу (додайте --dry-run флаг)
python3 -c "
from scripts.confluence import MockConfluenceAPI
api = MockConfluenceAPI()
pages = api.get_pages()
print(f'✓ Mock API: {len(pages)} сторінок')
for page in pages[:2]:
    print(f'  - {page[\"title\"]}')
"
```

3. **Перевіряйте вміст бази перед тестуванням**:
```bash
# Перевірка кількості документів
curl -X GET "http://localhost:6333/collections/qa_chunks" | jq '.result.points_count'

# Перевірка останніх документів
curl -X POST "http://localhost:6333/collections/qa_chunks/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": true}' | jq '.result.points[] | .payload.title'
```

#### Видалення тестових даних

Якщо ви випадково додали тестові дані:

```bash
# Видалення всіх мокнутих документів
curl -X POST "http://localhost:6333/collections/qa_chunks/points/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "confluence_page_id",
          "match": {
            "any": ["123456789", "123456790", "123456791", "234567890", "234567891", "345678901"]
          }
        }
      ]
    }
  }'
```

#### Перевірка після очищення

```bash
# Перевірка, що тестові дані видалені
curl -X POST "http://localhost:6333/collections/qa_chunks/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "confluence_page_id",
          "match": {
            "any": ["123456789", "123456790", "123456791", "234567890", "234567891", "345678901"]
          }
        }
      ]
    },
    "limit": 10
  }' | jq '.result.points | length'
# Має повернути 0
```

### Додавання нових функцій

1. **Mock API**: Додайте нові тестові дані в `confluence_mock.py`
2. **Real API**: Розширте методи в `confluence_real.py`
3. **Loader**: Оновіть логіку в `confluence_loader.py`

### Тестування

```bash
# Тест імпортів
python3 -c "from scripts.confluence import ConfluenceLoader, MockConfluenceAPI, RealConfluenceAPI; print('✓ Імпорти працюють')"

# Тест mock API (без збереження)
python3 -c "from scripts.confluence import MockConfluenceAPI; api = MockConfluenceAPI(); print(f'✓ Mock API: {len(api.get_pages())} сторінок')"
```

## 🐛 Усунення проблем

### ⚠️ Проблеми з тестовими даними

**Симптом**: В базі даних з'явилися фейкові документи з такими назвами:
- "Authentication Testing Checklist"
- "API Testing Guidelines" 
- "UI Testing Procedures"
- "Authentication Service Architecture"
- "Deployment Pipeline Documentation"
- "API Documentation Standards"

**Причина**: Запуск confluence_loader без флагу `--use-real-api` додає мокнуті дані.

**Рішення**:
```bash
# 1. Перевірте кількість документів
curl -X GET "http://localhost:6333/collections/qa_chunks" | jq '.result.points_count'

# 2. Видаліть тестові документи
curl -X POST "http://localhost:6333/collections/qa_chunks/points/delete" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"must": [{"key": "confluence_page_id", "match": {"any": ["123456789", "123456790", "123456791", "234567890", "234567891", "345678901"]}}]}}'

# 3. Перевірте, що видалення пройшло успішно
curl -X GET "http://localhost:6333/collections/qa_chunks" | jq '.result.points_count'
```

### Помилка з'єднання з Confluence
- Перевірте `CONFLUENCE_BASE_URL` та `CONFLUENCE_AUTH_TOKEN`
- Переконайтеся, що токен має права доступу до просторів
- Використайте `--test-connection` для діагностики

### Помилки з OpenAI API
- Перевірте `OPENAI_API_KEY`
- Переконайтеся, що у вас є кредити на API

### Помилки з векторною базою
- Перевірте, що Qdrant запущений
- Перевірте `VECTORDB_URL` в конфігурації

## 📝 Приклади використання

### Імпорт в Python коді

```python
from scripts.confluence import ConfluenceLoader, MockConfluenceAPI

# Використання mock API
loader = ConfluenceLoader(use_mock=True)
result = await loader.load_pages(space_keys=["QA"], once=True)

# Використання реального API
loader = ConfluenceLoader(use_mock=False)
result = await loader.load_pages(
    space_keys=["QA", "ENG"],
    labels=["checklist", "guide"],
    once=True
)
```

### Автоматизація завантаження

```bash
# Cron job для щоденного оновлення
0 2 * * * cd /path/to/qa_mcp && ./scripts/confluence/load_confluence_data.sh
```

## 🔗 Пов'язані модулі

- `app/data/vectordb_repo.py` - Робота з векторною базою даних
- `app/ai/embedder.py` - Генерація embeddings
- `app/config.py` - Конфігурація системи
- `app/mcp_tools.py` - MCP інструменти для пошуку
