# QA Analysis Scripts

Ця папка містить скрипти для аналізу структури QA чеклістів з Confluence та їх обробки за допомогою LLM.

## 📁 Структура файлів

- `analyze_qa_structure.py` - Аналізатор структури QA чеклістів
- `llm_checklist_analyzer.py` - LLM-аналізатор для складних чеклістів
- `README.md` - Ця документація

## 🔧 Передумови

### Системні вимоги
- Python 3.8+
- Віртуальне середовище з встановленими залежностями

### Налаштування середовища
```bash
# Активація віртуального середовища
source venv/bin/activate

# Перевірка залежностей
pip list | grep -E "(click|openai|atlassian)"
```

### Конфігурація
Створіть файл `.env` в корені проекту з наступними змінними:

```env
# Confluence API
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_AUTH_TOKEN=your_token_here
CONFLUENCE_ROOT_PAGES=page_id1,page_id2

# OpenAI API
OPENAI_API_KEY=your_openai_key_here
```

## 📋 analyze_qa_structure.py

### Призначення
Аналізує структуру QA чеклістів у Confluence, витягує тесткейси з таблиць та створює структуровані дані.

### Функціональність
- ✅ Рекурсивний аналіз QA секцій та дочірніх сторінок
- ✅ Автоматичне виявлення таблиць з тесткейсами
- ✅ Парсинг тесткейсів з полями: step, expected_result, priority, config
- ✅ Розпізнавання категорій GENERAL/CUSTOM
- ✅ Експорт результатів у JSON формат

### Використання

#### Аналіз конкретної сторінки
```bash
python scripts/analyze/analyze_qa_structure.py \
  --page-id 123456 \
  --output results.json
```

#### Аналіз сторінок з конфігурації
```bash
python scripts/analyze/analyze_qa_structure.py \
  --use-config \
  --output results.json
```

#### Параметри
- `--page-id` - ID сторінки Confluence для аналізу
- `--use-config` - Використовувати сторінки з `CONFLUENCE_ROOT_PAGES`
- `--output` - Файл для збереження результатів (JSON)

### Приклад виводу
```json
{
  "123456": {
    "simple_analysis": {
      "page": {...},
      "structure": {
        "type": "checklist",
        "has_testcases": true,
        "testcases": [...]
      }
    },
    "qa_section": {
      "title": "Checklist WEB",
      "checklists_count": 5,
      "total_testcases": 150
    }
  }
}
```

## 🤖 llm_checklist_analyzer.py

### Призначення
Використовує GPT-4 для розбору складних чеклістів з нестандартною структурою та високою точністю аналізу.

### Функціональність
- ✅ LLM-аналіз HTML контенту чеклістів
- ✅ Витягування структурованої інформації
- ✅ Оцінка впевненості в правильності розбору
- ✅ Fallback механізм при помилках LLM
- ✅ Batch обробка множинних чеклістів

### Використання

#### Аналіз чеклістів з JSON файлу
```bash
python scripts/analyze/llm_checklist_analyzer.py \
  --input-file input.json \
  --output-file output.json \
  --confidence-threshold 0.7
```

#### Параметри
- `--input-file` - JSON файл з чеклістами (результат `analyze_qa_structure.py`)
- `--output-file` - Файл для збереження результатів
- `--confidence-threshold` - Мінімальна впевненість (0.0-1.0, за замовчуванням 0.7)

### Приклад виводу
```json
{
  "high_confidence": [
    {
      "title": "WEB: Billing History",
      "description": "Тестування функціональності історії платежів",
      "testcases": [
        {
          "step": "Перейти до розділу Billing",
          "expected_result": "Відображається список платежів",
          "priority": "HIGH",
          "test_group": "GENERAL"
        }
      ],
      "confidence": 0.95
    }
  ],
  "low_confidence": [...],
  "summary": {
    "total_checklists": 10,
    "high_confidence_count": 8,
    "low_confidence_count": 2
  }
}
```

## 🔄 Workflow використання

### 1. Базовий аналіз структури
```bash
# Аналізуємо QA секції
python scripts/analyze/analyze_qa_structure.py \
  --use-config \
  --output structure_analysis.json
```

### 2. LLM-аналіз складних чеклістів
```bash
# Обробляємо результати через LLM
python scripts/analyze/llm_checklist_analyzer.py \
  --input-file structure_analysis.json \
  --output-file llm_analysis.json \
  --confidence-threshold 0.8
```

### 3. Завантаження в БД
Результати можна завантажити в базу даних через `QARepository` або MCP сервер.

## 🛠️ Технічні деталі

### Залежності
- `click` - CLI інтерфейс
- `openai` - GPT-4 API
- `atlassian-python-api` - Confluence API
- `app.config` - Конфігурація проекту
- `scripts.confluence.confluence_real` - Confluence клієнт

### Структура даних
Скрипти працюють з моделями з `app.models.qa_models`:
- `QASection` - кореневі секції (Checklist WEB, Checklist MOB)
- `Checklist` - сторінки з тесткейсами
- `TestCase` - індивідуальні тесткейси
- `Config` - конфігурації

### Обробка помилок
- ✅ Graceful fallback при помилках LLM
- ✅ Валідація вхідних даних
- ✅ Детальне логування помилок
- ✅ Продовження роботи при помилках окремих сторінок

## 📊 Моніторинг та логування

### Логи аналізу
Скрипти виводять детальну інформацію про процес:
```
Аналізую сторінку 123456...
Назва сторінки: Checklist WEB
Знайдена таблиця з заголовками: ['Step', 'Expected Result', 'Priority']
Знайдено 25 тесткейсів у таблиці
```

### Метрики якості
- Кількість оброблених сторінок
- Кількість знайдених тесткейсів
- Рівень впевненості LLM аналізу
- Частота помилок

## 🔧 Налагодження

### Типові проблеми

#### Помилка підключення до Confluence
```
Error: CONFLUENCE_AUTH_TOKEN не встановлений
```
**Рішення:** Перевірте налаштування в `.env` файлі

#### Помилка OpenAI API
```
Error: OPENAI_API_KEY не встановлений
```
**Рішення:** Встановіть валідний API ключ OpenAI

#### Помилка імпорту модулів
```
ModuleNotFoundError: No module named 'qdrant_client'
```
**Рішення:** Активуйте віртуальне середовище та встановіть залежності

### Режим налагодження
Для детального логування додайте в код:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Продуктивність

### Оптимізація
- Обмеження довжини контенту для LLM (8000 символів)
- Batch обробка чеклістів
- Кешування результатів аналізу
- Паралельна обробка незалежних сторінок

### Рекомендації
- Використовуйте `analyze_qa_structure.py` для швидкого аналізу
- Застосовуйте `llm_checklist_analyzer.py` для складних випадків
- Встановіть `confidence_threshold` відповідно до ваших вимог
- Регулярно оновлюйте результати аналізу

## 🤝 Внесок у розробку

### Додавання нових аналізаторів
1. Створіть новий файл в папці `analyze/`
2. Додайте CLI інтерфейс з `click`
3. Використовуйте спільні компоненти з `app/`
4. Оновіть цей README.md

### Тестування
```bash
# Тест базової функціональності
python scripts/analyze/analyze_qa_structure.py --help
python scripts/analyze/llm_checklist_analyzer.py --help

# Тест з реальними даними (потребує налаштування)
python scripts/analyze/analyze_qa_structure.py --use-config --output test.json
```

---

**Примітка:** Ці скрипти є автономними утилітами для аналізу QA даних. Вони не інтегровані безпосередньо в основну систему, але можуть бути використані для підготовки даних перед завантаженням в БД.
