# Продакшн розгортання QA MCP сервера

Цей документ містить детальні рекомендації для розгортання QA MCP сервера в продакшн середовищі.

## Передумови

### Системні вимоги

**Мінімальні:**
- CPU: 2 ядра
- RAM: 4 GB
- Диск: 20 GB SSD
- Мережа: 100 Mbps

**Рекомендовані:**
- CPU: 4+ ядра
- RAM: 8+ GB
- Диск: 50+ GB SSD
- Мережа: 1 Gbps

### Операційна система

- Ubuntu 20.04 LTS або новіша
- CentOS 8+ або RHEL 8+
- Debian 11+

### Програмне забезпечення

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Nginx (опціонально)
- SSL сертифікати

## Архітектура продакшн системи

### Компоненти

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cursor IDE    │    │   Load Balancer │    │   MCP Server    │
│                 │◄──►│   (Nginx)       │◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐            │
                       │   MySQL DB      │◄───────────┤
                       │   (Primary)     │            │
                       └─────────────────┘            │
                                                       │
                       ┌─────────────────┐            │
                       │   Qdrant        │◄───────────┘
                       │   (Vector DB)   │
                       └─────────────────┘
```

### Мережева архітектура

```
Internet
    │
    ▼
┌─────────────┐
│   Firewall  │ (UFW/iptables)
└─────────────┘
    │
    ▼
┌─────────────┐
│   Nginx     │ (Reverse Proxy + SSL)
└─────────────┘
    │
    ▼
┌─────────────┐
│ MCP Server  │ (Docker Container)
└─────────────┘
    │
    ├──► MySQL (Docker Container)
    └──► Qdrant (Docker Container)
```

## Покрокове розгортання

### Крок 1: Підготовка сервера

```bash
# Оновлення системи
sudo apt update && sudo apt upgrade -y

# Встановлення необхідних пакетів
sudo apt install -y curl wget git htop ufw fail2ban

# Налаштування часового поясу
sudo timedatectl set-timezone Europe/Kiev

# Створення користувача для додатку
sudo useradd -m -s /bin/bash qa-mcp
sudo usermod -aG docker qa-mcp
```

### Крок 2: Встановлення Docker

```bash
# Автоматичне встановлення через скрипт
sudo ./scripts/setup_production_server.sh --port 3000

# Або ручне встановлення
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Крок 3: Клонування проекту

```bash
# Клонування репозиторію
git clone https://github.com/your-org/qa_mcp.git
cd qa_mcp

# Налаштування прав
sudo chown -R qa-mcp:qa-mcp /path/to/qa_mcp
```

### Крок 4: Конфігурація

```bash
# Копіювання конфігурації
cp env.example .env

# Редагування конфігурації
nano .env
```

**Продакшн конфігурація `.env`:**
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Database Configuration
MYSQL_DSN=mysql+pymysql://qa:secure_password@mysql:3306/qa
VECTORDB_URL=http://qdrant:6333

# Application Configuration
APP_PORT=3000
MAX_TOP_K=50
ENVIRONMENT=production

# Security
SECRET_KEY=your_very_secure_secret_key_here
ALLOWED_HOSTS=your-domain.com,localhost

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Крок 5: Ініціалізація баз даних

```bash
# Ініціалізація з нуля
./scripts/init_production_db.sh --fresh --force

# Або відновлення з бекапу
./scripts/init_production_db.sh backups/production_backup.tar.gz
```

### Крок 6: Налаштування системних сервісів

```bash
# Автоматичне налаштування
sudo ./scripts/setup_production_server.sh \
  --port 3000 \
  --systemd \
  --firewall \
  --reverse-proxy \
  --nginx-config \
  --monitoring \
  --backup
```

### Крок 7: SSL сертифікати

```bash
# З Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Або з власними сертифікатами
sudo ./scripts/setup_production_server.sh \
  --ssl \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem
```

### Крок 8: Тестування

```bash
# Тест системи
curl https://your-domain.com/health

# Тест MCP endpoint
curl -X POST https://your-domain.com/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'

# Тест з Cursor
# Налаштуйте ~/.cursor/mcp.json з URL вашого сервера
```

## Безпека

### Firewall налаштування

```bash
# Базові правила
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Додаткові правила для моніторингу
sudo ufw allow from 10.0.0.0/8 to any port 3000
sudo ufw allow from 192.168.0.0/16 to any port 3000

# Увімкнення firewall
sudo ufw enable
```

### Fail2ban налаштування

```bash
# Створення конфігурації для Nginx
sudo nano /etc/fail2ban/jail.local
```

```ini
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
```

### SSL/TLS налаштування

```nginx
# /etc/nginx/sites-available/qa-mcp-server
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Аутентифікація

```bash
# Створення файлу паролів для базової аутентифікації
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Додавання користувачів
sudo htpasswd /etc/nginx/.htpasswd user1
sudo htpasswd /etc/nginx/.htpasswd user2
```

## Моніторинг

### Системний моніторинг

```bash
# Встановлення Prometheus та Grafana
sudo apt install prometheus grafana

# Налаштування Prometheus
sudo nano /etc/prometheus/prometheus.yml
```

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'qa-mcp-server'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Логування

```bash
# Налаштування централізованого логування
sudo apt install rsyslog

# Конфігурація для Docker логів
sudo nano /etc/rsyslog.d/50-docker.conf
```

```
# Docker logs
:programname, isequal, "docker" /var/log/docker.log
& stop
```

### Алерти

```bash
# Створення скрипта для алертів
sudo nano /usr/local/bin/qa-mcp-alerts.sh
```

```bash
#!/bin/bash
# Алерти для QA MCP сервера

LOG_FILE="/var/log/qa-mcp-alerts.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Функція для відправки алерту
send_alert() {
    local message="$1"
    echo "[$DATE] ALERT: $message" >> "$LOG_FILE"
    
    # Відправка email (налаштуйте sendmail або postfix)
    echo "$message" | mail -s "QA MCP Server Alert" admin@your-domain.com
    
    # Відправка в Slack (опціонально)
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"QA MCP Server Alert: $message\"}" \
        https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
}

# Перевірка статусу
if ! systemctl is-active --quiet qa-mcp-server; then
    send_alert "QA MCP Server service is down"
fi

if ! curl -s http://localhost:3000/health > /dev/null; then
    send_alert "QA MCP Server HTTP endpoint is not responding"
fi

# Перевірка використання диска
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    send_alert "Disk usage is ${DISK_USAGE}%"
fi

# Перевірка використання пам'яті
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -gt 80 ]; then
    send_alert "Memory usage is ${MEM_USAGE}%"
fi
```

## Бекапи

### Автоматичні бекапи

```bash
# Налаштування cron job для бекапів
crontab -e
```

```
# Щоденний бекап о 2:00
0 2 * * * /usr/local/bin/qa-mcp-backup.sh

# Щотижневий бекап в неділю о 3:00
0 3 * * 0 /usr/local/bin/qa-mcp-backup.sh --full

# Щомісячний бекап 1 числа о 4:00
0 4 1 * * /usr/local/bin/qa-mcp-backup.sh --archive
```

### Зовнішнє зберігання

```bash
# Налаштування S3 для бекапів
sudo apt install awscli

# Конфігурація AWS
aws configure

# Скрипт для завантаження в S3
sudo nano /usr/local/bin/backup-to-s3.sh
```

```bash
#!/bin/bash
# Завантаження бекапів в S3

BACKUP_DIR="/var/backups/qa-mcp"
S3_BUCKET="your-qa-mcp-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Створення бекапу
cd /path/to/qa_mcp
./scripts/backup_database.sh "s3_backup_$DATE"

# Завантаження в S3
aws s3 cp "$BACKUP_DIR/s3_backup_$DATE.tar.gz" "s3://$S3_BUCKET/"

# Видалення локальних бекапів старше 7 днів
find "$BACKUP_DIR" -name "s3_backup_*.tar.gz" -mtime +7 -delete
```

## Масштабування

### Горизонтальне масштабування

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mcp-server-1
      - mcp-server-2
      - mcp-server-3

  mcp-server-1:
    build: .
    environment:
      - INSTANCE_ID=1
    depends_on:
      - mysql
      - qdrant

  mcp-server-2:
    build: .
    environment:
      - INSTANCE_ID=2
    depends_on:
      - mysql
      - qdrant

  mcp-server-3:
    build: .
    environment:
      - INSTANCE_ID=3
    depends_on:
      - mysql
      - qdrant

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secure_password
    volumes:
      - mysql_data:/var/lib/mysql

  qdrant:
    image: qdrant/qdrant:v1.15.1
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  mysql_data:
  qdrant_data:
```

### Вертикальне масштабування

```bash
# Налаштування ресурсів для Docker
sudo nano /etc/docker/daemon.json
```

```json
{
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Оптимізація продуктивності

### База даних

```sql
-- MySQL оптимізація
SET GLOBAL innodb_buffer_pool_size = 2G;
SET GLOBAL innodb_log_file_size = 256M;
SET GLOBAL max_connections = 200;

-- Індекси для швидкого пошуку
CREATE INDEX idx_testcase_functionality ON testcases(functionality);
CREATE INDEX idx_testcase_priority ON testcases(priority);
CREATE INDEX idx_checklist_section ON checklists(section_id);
```

### Qdrant оптимізація

```yaml
# qdrant-config.yaml
storage:
  # Використання SSD
  storage_path: "/qdrant/storage"
  
  # Оптимізація пам'яті
  on_disk_payload: true
  
  # Паралельність
  max_optimization_threads: 4

service:
  # Кешування
  enable_cors: true
  
  # Логування
  log_level: "INFO"
```

### Nginx оптимізація

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
worker_cpu_affinity auto;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    # Кешування
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    # Gzip стиснення
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

## Підтримка та обслуговування

### Регулярні завдання

```bash
# Щоденні завдання
0 1 * * * /usr/local/bin/qa-mcp-daily-maintenance.sh

# Щотижневі завдання
0 2 * * 0 /usr/local/bin/qa-mcp-weekly-maintenance.sh

# Щомісячні завдання
0 3 1 * * /usr/local/bin/qa-mcp-monthly-maintenance.sh
```

### Оновлення

```bash
# Скрипт для оновлення
sudo nano /usr/local/bin/qa-mcp-update.sh
```

```bash
#!/bin/bash
# Оновлення QA MCP сервера

set -e

PROJECT_DIR="/path/to/qa_mcp"
BACKUP_DIR="/var/backups/qa-mcp"

echo "🔄 Початок оновлення QA MCP сервера..."

# Створення бекапу
cd "$PROJECT_DIR"
./scripts/backup_database.sh "update_backup_$(date +%Y%m%d_%H%M%S)"

# Зупинка сервісів
sudo systemctl stop qa-mcp-server

# Оновлення коду
git pull origin main

# Перебудова контейнерів
docker compose build --no-cache

# Запуск сервісів
sudo systemctl start qa-mcp-server

# Тестування
sleep 30
if curl -s http://localhost:3000/health > /dev/null; then
    echo "✅ Оновлення завершено успішно"
else
    echo "❌ Помилка після оновлення, відновлення з бекапу..."
    # Логіка відновлення
fi
```

## Troubleshooting

### Типові проблеми

1. **Високе використання CPU**
   - Перевірте логи на завислі запити
   - Оптимізуйте запити до бази даних
   - Додайте індекси

2. **Високе використання пам'яті**
   - Перевірте на витоки пам'яті
   - Збільшіть swap
   - Оптимізуйте кешування

3. **Повільні відповіді**
   - Перевірте мережеве підключення
   - Оптимізуйте базу даних
   - Додайте кешування

### Команди діагностики

```bash
# Системні ресурси
htop
iotop
nethogs

# Docker ресурси
docker stats
docker system df
docker system prune

# Мережеві з'єднання
netstat -tlnp
ss -tlnp
lsof -i :3000

# Логи
journalctl -u qa-mcp-server -f
docker compose logs -f
tail -f /var/log/nginx/access.log
```

## Контрольний список розгортання

### Перед розгортанням

- [ ] Системні вимоги перевірені
- [ ] Docker та Docker Compose встановлені
- [ ] Firewall налаштований
- [ ] SSL сертифікати отримані
- [ ] Конфігурація `.env` налаштована
- [ ] Бази даних ініціалізовані

### Після розгортання

- [ ] Сервіси запущені та працюють
- [ ] HTTP endpoints відповідають
- [ ] MCP інструменти доступні
- [ ] Моніторинг налаштований
- [ ] Бекапи працюють
- [ ] Алерти налаштовані
- [ ] Документація оновлена

### Регулярне обслуговування

- [ ] Моніторинг логів
- [ ] Перевірка ресурсів
- [ ] Оновлення залежностей
- [ ] Тестування бекапів
- [ ] Оновлення сертифікатів
- [ ] Аналіз продуктивності

## Підтримка

Для отримання підтримки:

1. Перевірте логи системи
2. Перегляньте документацію
3. Створіть issue в репозиторії
4. Зверніться до команди розробки

**Контакти:**
- Email: support@your-domain.com
- Slack: #qa-mcp-support
- GitHub Issues: https://github.com/your-org/qa_mcp/issues
