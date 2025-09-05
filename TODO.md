# MCP QA Search Server - План подальших кроків

## 📋 Загальний огляд

Поточний стан: MVP v.0.1 реалізовано та готовий до production. Система працює локально з мок-даними та підтримує базовий функціонал пошуку по документах.

**Наступні етапи розвитку:**

---

## 🎯 Фаза 1: Реальні дані з Confluence

### 1.1 Інтеграція з реальним Confluence API
#### Завдання:
- [ ] Створити реальний Confluence API клієнт
  - [ ] Імплементувати автентифікацію (Personal Access Token)
  - [ ] Додати методи для отримання сторінок з фільтрами
  - [ ] Обробка rate limiting та пагінації
  - [ ] Валідація permissions для доступу до просторів

- [ ] Розширити конфігурацію
  - [ ] Додати змінні `CONFLUENCE_BASE_URL`, `CONFLUENCE_AUTH_TOKEN`
  - [ ] Налаштувати SSL/TLS для HTTPS підключень
  - [ ] Додати параметри для rate limiting

- [ ] Оновити confluence_loader.py
  - [ ] Замінити MockConfluenceAPI на RealConfluenceAPI
  - [ ] Додати обробку помилок API (403, 404, 429)
  - [ ] Імплементувати інкрементальне завантаження
  - [ ] Додати логування API викликів

#### Технічні деталі:
```python
# Нові змінні в config.py
confluence_base_url: str = "https://your-domain.atlassian.net/wiki"
confluence_auth_token: str  # Personal Access Token
confluence_user_email: Optional[str] = None  # Для Basic Auth
confluence_api_timeout: int = 30
confluence_max_retries: int = 3
```

#### Тестування:
- [ ] Створити тестове підключення до Confluence
- [ ] Завантажити 10-20 реальних сторінок
- [ ] Перевірити якість chunking та feature detection
- [ ] Протестувати інкрементальне оновлення

---

## 🗄️ Фаза 2: Модель даних для тесткейсів

### 2.1 Нова структура даних
**Пріоритет:** Високий  
**Складність:** Висока  
**Час:** 5-7 днів  

#### Поточна проблема:
Зараз система зберігає документи як суцільний текст, розбитий на чанки. Потрібно зберігати тесткейси як окремі атомарні одиниці з зв'язками до фіч та чеклистів.

#### Нова модель даних:

```sql
-- Таблиця для чеклистів (групи тесткейсів)
CREATE TABLE checklists (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    confluence_page_id VARCHAR(64) UNIQUE,
    space_key VARCHAR(64) NOT NULL,
    feature_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE SET NULL
);

-- Таблиця для тесткейсів
CREATE TABLE test_cases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(512) NOT NULL,
    description TEXT,
    steps TEXT,  -- JSON array of steps
    expected_result TEXT,
    priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    test_type ENUM('functional', 'security', 'performance', 'ui', 'api') DEFAULT 'functional',
    checklist_id INT NOT NULL,
    feature_id INT,
    ordinal_position INT DEFAULT 0,
    is_automated BOOLEAN DEFAULT FALSE,
    tags JSON,  -- Additional tags like ["regression", "smoke"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
    FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE SET NULL,
    INDEX idx_checklist_ordinal (checklist_id, ordinal_position),
    INDEX idx_feature_priority (feature_id, priority),
    INDEX idx_test_type (test_type)
);

-- Зв'язок тесткейсів з додатковими фічами (many-to-many)
CREATE TABLE test_case_features (
    test_case_id INT,
    feature_id INT,
    relevance_score FLOAT DEFAULT 1.0,
    PRIMARY KEY (test_case_id, feature_id),
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);
```

#### Завдання:
- [ ] Створити нові SQLAlchemy моделі
  - [ ] `Checklist` модель з зв'язками
  - [ ] `TestCase` модель з полями для структурованих даних
  - [ ] `TestCaseFeature` association table
  - [ ] Міграції для оновлення схеми БД

- [ ] Оновити parser для Confluence сторінок
  - [ ] Розпізнавати чеклисти в markdown форматі
  - [ ] Парсити окремі тесткейси з чеклистів
  - [ ] Витягувати структуровані дані (steps, expected results)
  - [ ] Визначати пріоритет та тип тестів

- [ ] Розширити векторну БД структуру
  - [ ] Зберігати embeddings для кожного тесткейсу окремо
  - [ ] Додати метадані: checklist_id, test_case_id, priority
  - [ ] Оновити search для пошуку по тесткейсам

#### Нові MCP інструменти:
- [ ] `qa_search_testcases` - пошук конкретних тесткейсів
- [ ] `qa_get_checklist` - отримання повного чеклиста
- [ ] `qa_testcases_by_feature` - тесткейси для фічі
- [ ] `qa_list_checklists` - список всіх чеклистів

### 2.2 Розширений парсер контенту
**Завдання:**
- [ ] Імплементувати `ChecklistParser` клас
  - [ ] Розпізнавати різні формати чеклистів (markdown, Confluence макроси)
  - [ ] Витягувати structured data з описів тестів
  - [ ] Автоматично визначати пріоритет на основі ключових слів
  - [ ] Класифікувати тип тестування (functional, security, etc.)

```python
# Приклад структури парсера
class ChecklistParser:
    def parse_confluence_page(self, page_content: str) -> List[TestCase]:
        # Розпізнати чеклисти в контенті
        # Витягти окремі тест-кейси
        # Структурувати дані
        pass
    
    def extract_test_steps(self, test_description: str) -> List[str]:
        # Витягти кроки тестування
        pass
    
    def determine_priority(self, test_content: str) -> str:
        # Автоматично визначити пріоритет
        pass
```

---

## 🚀 Фаза 3: Production Deployment

### 3.1 Налаштування віддаленого сервера
**Пріоритет:** Середній  
**Складність:** Середня  
**Час:** 3-4 дні  

#### Завдання:
- [ ] Підготувати production Docker setup
  - [ ] Створити production docker-compose.yml
  - [ ] Налаштувати SSL/TLS сертифікати
  - [ ] Додати reverse proxy (nginx)
  - [ ] Налаштувати логування та моніторинг

- [ ] Безпека та автентифікація
  - [ ] Додати API ключі для MCP підключень
  - [ ] Налаштувати CORS для веб-доступу
  - [ ] Імплементувати rate limiting
  - [ ] Додати IP whitelist для критичних операцій

- [ ] Конфігурація production середовища
  - [ ] Змінні для production БД (PostgreSQL)
  - [ ] Налаштування для віддаленого Qdrant
  - [ ] Backup стратегії для даних
  - [ ] Health checks та alerting

#### Production docker-compose.yml:
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - mcp-server

  mcp-server:
    build: .
    environment:
      ENVIRONMENT: production
      MYSQL_DSN: postgresql://user:pass@prod-db:5432/qa
      VECTORDB_URL: http://prod-qdrant:6333
      API_KEY: ${PRODUCTION_API_KEY}
    # Не експонувати порт назовні
    expose:
      - "3000"
```

### 3.2 Віддалене підключення з Cursor
**Завдання:**
- [ ] Створити безпечний MCP клієнт для віддалених підключень
  - [ ] HTTP client з API key автентифікацією
  - [ ] SSL certificate validation
  - [ ] Connection pooling та retry logic
  - [ ] Error handling та fallback

- [ ] Оновити mcp_local.py для підтримки віддалених серверів
```python
# Нова конфігурація в ~/.cursor/mcp.json
{
  "mcpServers": {
    "qa-search-remote": {
      "command": "python3",
      "args": ["/path/to/qa_mcp/mcp_remote_client.py"],
      "env": {
        "QA_MCP_SERVER_URL": "https://your-server.com",
        "QA_MCP_API_KEY": "your-api-key"
      }
    }
  }
}
```

- [ ] Створити моніторинг та діагностику
  - [ ] Health check endpoints
  - [ ] Performance metrics
  - [ ] Connection status dashboard
  - [ ] Automated testing віддаленого підключення

### 3.3 Deployment автоматизація
**Завдання:**
- [ ] CI/CD pipeline
  - [ ] GitHub Actions / GitLab CI для автоматичного deployment
  - [ ] Automated testing перед deployment
  - [ ] Blue-green deployment strategy
  - [ ] Rollback mechanism

- [ ] Infrastructure as Code
  - [ ] Terraform/Ansible скрипти для server setup
  - [ ] Automated SSL certificate management (Let's Encrypt)
  - [ ] Database migration scripts
  - [ ] Backup automation

---

## 📊 Додаткові покращення

### 4.1 Розширений пошук (Фаза 4)
- [ ] Гібридний пошук (vector + BM25)
- [ ] Cross-encoder re-ranking
- [ ] Фільтрація по типу тестів, пріоритету
- [ ] Пошук по кроках тестування
- [ ] Similarity search для схожих тесткейсів

### 4.2 UI Dashboard (Фаза 5)
- [ ] Web інтерфейс для перегляду даних
- [ ] Статистика по фічам та тесткейсам
- [ ] Візуалізація coverage по фічам
- [ ] Інтерактивний пошук та фільтрація

### 4.3 Інтеграції (Фаза 6)
- [ ] Jira integration для test execution tracking
- [ ] TestRail integration
- [ ] Slack notifications для оновлень
- [ ] API для зовнішніх систем

---

## 🎯 Пріоритизація

### Високий пріоритет (наступні 2 тижні):
1. **Реальний Confluence API** - критично для практичного використання
2. **Модель тесткейсів** - основа для специфічного QA use case

### Середній пріоритет (наступний місяць):
3. **Production deployment** - необхідно для team використання

### Низький пріоритет (майбутні релізи):
4. Розширений пошук
5. UI Dashboard
6. Додаткові інтеграції

---

## 📈 Метрики успіху

### Фаза 1 (Реальні дані):
- [ ] Успішно завантажено >100 реальних сторінок
- [ ] Якість feature detection >80% точність
- [ ] Час завантаження <2 сек на сторінку

### Фаза 2 (Тесткейси):
- [ ] Розпарсено >500 тесткейсів
- [ ] Структуровані дані для >90% тестів
- [ ] Пошук по тесткейсам працює <1 сек

### Фаза 3 (Production):
- [ ] 99.9% uptime
- [ ] <500ms response time
- [ ] Безпечне віддалене підключення працює

---

## 🔧 Технічні вимоги

### Розробка:
- Python 3.9+
- Docker & docker-compose
- MySQL/PostgreSQL
- Qdrant
- OpenAI API

### Production:
- Linux сервер (Ubuntu 20.04+)
- 4+ GB RAM
- SSL сертифікат
- Доменне ім'я
- Backup стратегія

### Безпека:
- API ключі для всіх зовнішніх сервісів
- HTTPS обов'язково для production
- Regular security updates
- Access logging та monitoring
