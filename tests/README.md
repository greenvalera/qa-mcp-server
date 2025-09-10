# QA MCP Server Tests

Ця папка містить тести для QA MCP сервера, включаючи unit тести та інтеграційні тести.

## 📁 Структура файлів

- `test_basic.py` - Базові unit тести для компонентів системи
- `test_mcp_client.py` - Інтеграційні тести MCP сервера через HTTP API
- `README.md` - Ця документація

## 🧪 Типи тестів

### Unit тести (`test_basic.py`)

Тестують окремі компоненти системи:

- **TestConfiguration** - тестування конфігурації
- **TestMockConfluenceAPI** - тестування mock Confluence API
- **TestEmbedder** - тестування OpenAI embedder
- **TestMCPToolBase** - тестування базової функціональності MCP інструментів

### Інтеграційні тести (`test_mcp_client.py`)

Тестують повну функціональність MCP сервера через HTTP API:

- **Health Check** - перевірка стану системи
- **List Features** - тестування списку фіч
- **Docs by Feature** - тестування документів за фічею
- **Search** - тестування пошуку
- **HTTP API** - тестування REST endpoints

## 🚀 Запуск тестів

### Передумови

```bash
# Активація віртуального середовища
source venv/bin/activate

# Встановлення залежностей
pip install -r app/requirements.txt
```

### Unit тести (pytest)

```bash
# Запуск всіх unit тестів
pytest tests/test_basic.py -v

# Запуск конкретного тесту
pytest tests/test_basic.py::TestConfiguration::test_settings_creation -v

# Запуск з покриттям коду
pytest tests/test_basic.py --cov=app --cov-report=html
```

### Інтеграційні тести (MCP Client)

```bash
# Запуск всіх інтеграційних тестів
python tests/test_mcp_client.py

# Запуск конкретного тесту
python tests/test_mcp_client.py --test health
python tests/test_mcp_client.py --test search
python tests/test_mcp_client.py --test features

# Тестування з іншим URL
python tests/test_mcp_client.py --url http://localhost:3000 --test all
```

### Всі тести разом

```bash
# Unit тести
pytest tests/test_basic.py -v

# Інтеграційні тести (потребує запущеного сервера)
python tests/test_mcp_client.py --test all
```

## 🔧 Налаштування для тестування

### Unit тести

Unit тести не потребують зовнішніх сервісів - вони використовують mock об'єкти.

### Інтеграційні тести

Інтеграційні тести потребують запущеного MCP сервера:

```bash
# Запуск сервера (в окремому терміналі)
docker compose up -d

# Або локально
python app/mcp_server.py
```

## 📊 Результати тестування

### Unit тести

```
tests/test_basic.py::TestConfiguration::test_settings_creation PASSED
tests/test_basic.py::TestConfiguration::test_environment_detection PASSED
tests/test_basic.py::TestMockConfluenceAPI::test_mock_api_creation PASSED
...
```

### Інтеграційні тести

```
🚀 Starting MCP QA Search Server tests...

🔍 Testing qa.health...
  ✅ Vector DB: healthy
  ✅ MySQL: healthy
  ✅ OpenAI: healthy
  📊 Documents: 25
  📊 Features: 8
  📊 Chunks: 150

🔍 Testing qa.list_features...
  ✅ Found 8 features (total: 8)
    • Authentication: User authentication and authorization...
      Documents: 3
    • API Testing: API endpoint testing procedures...
      Documents: 5

📊 Test Results: 5/5 tests passed
🎉 All tests passed!
```

## 🐛 Налагодження тестів

### Проблеми з unit тестами

```bash
# Детальний вивід
pytest tests/test_basic.py -v -s

# З traceback
pytest tests/test_basic.py --tb=long

# Тільки failed тести
pytest tests/test_basic.py --lf
```

### Проблеми з інтеграційними тестами

```bash
# Перевірка доступності сервера
curl http://localhost:3000/health

# Тест з детальним виводом
python tests/test_mcp_client.py --test health -v

# Перевірка логів сервера
docker compose logs mcp-server
```

## 📝 Написання нових тестів

### Unit тести

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    """Test new feature functionality."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = function_under_test()
        
        # Assert
        assert result == expected
    
    @patch('module.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependency."""
        mock_dependency.return_value = "mocked_value"
        
        result = function_under_test()
        
        assert result == "expected_result"
        mock_dependency.assert_called_once()
```

### Інтеграційні тести

```python
async def test_new_mcp_tool(self) -> bool:
    """Test new MCP tool."""
    click.echo("🔍 Testing new.tool...")
    try:
        result = await self.call_tool("new.tool", {
            "param1": "value1",
            "param2": "value2"
        })
        
        if "error" in result:
            click.echo(f"  ❌ Error: {result['error']}")
            return False
        
        # Validate result
        assert "expected_field" in result["result"]
        click.echo("  ✅ New tool test passed")
        return True
        
    except Exception as e:
        click.echo(f"  ❌ New tool test failed: {e}")
        return False
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      
      - name: Install dependencies
        run: |
          pip install -r app/requirements.txt
      
      - name: Run unit tests
        run: pytest tests/test_basic.py -v
      
      - name: Start services
        run: docker compose up -d
      
      - name: Run integration tests
        run: python tests/test_mcp_client.py --test all
```

## 📈 Метрики якості

### Покриття коду

```bash
# Генерація звіту покриття
pytest tests/test_basic.py --cov=app --cov-report=html --cov-report=term

# Перегляд звіту
open htmlcov/index.html
```

### Профілювання

```bash
# Профілювання тестів
pytest tests/test_basic.py --profile

# Аналіз швидкості
pytest tests/test_basic.py --durations=10
```

## 🎯 Best Practices

### Unit тести

1. **Один тест = одна перевірка**
2. **Використовуйте mock для зовнішніх залежностей**
3. **Тестуйте граничні випадки**
4. **Назви тестів повинні описувати що тестується**

### Інтеграційні тести

1. **Тестуйте реальні сценарії використання**
2. **Перевіряйте повний workflow**
3. **Тестуйте обробку помилок**
4. **Використовуйте реальні дані коли можливо**

### Загальні принципи

1. **Тести повинні бути швидкими та надійними**
2. **Не залежати від зовнішніх сервісів (крім інтеграційних)**
3. **Очищати після себе (teardown)**
4. **Документувати складні тести**

---

**Примітка:** Ці тести є частиною системи забезпечення якості QA MCP сервера. Регулярне виконання тестів допомагає виявляти проблеми на ранніх етапах розробки.
