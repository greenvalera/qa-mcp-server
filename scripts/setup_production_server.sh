#!/bin/bash
# Скрипт для налаштування продакшн сервера MCP
# Використання: ./scripts/setup_production_server.sh [options]

set -e

# Конфігурація
SERVER_PORT="3000"
HTTP_PORT="3000"
ENVIRONMENT="production"
SSL_ENABLED=false
SSL_CERT=""
SSL_KEY=""
REVERSE_PROXY=false
NGINX_CONFIG=false

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для показу довідки
show_help() {
    echo -e "${GREEN}🔧 QA MCP Server - Production Server Setup${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    echo ""
    echo "Використання: $0 [options]"
    echo ""
    echo "Опції:"
    echo "  --port PORT            - Порт для MCP сервера (default: 3000)"
    echo "  --http-port PORT       - Порт для HTTP API (default: 3000)"
    echo "  --ssl                  - Увімкнути SSL/TLS"
    echo "  --ssl-cert PATH        - Шлях до SSL сертифікату"
    echo "  --ssl-key PATH         - Шлях до SSL приватного ключа"
    echo "  --reverse-proxy        - Налаштувати reverse proxy (Nginx)"
    echo "  --nginx-config         - Генерувати конфігурацію Nginx"
    echo "  --systemd              - Створити systemd сервіс"
    echo "  --firewall             - Налаштувати firewall"
    echo "  --monitoring           - Налаштувати моніторинг"
    echo "  --backup               - Налаштувати автоматичні бекапи"
    echo "  --help                 - Показати цю довідку"
    echo ""
    echo "Приклади:"
    echo "  $0 --port 3000 --systemd --firewall"
    echo "  $0 --ssl --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem"
    echo "  $0 --reverse-proxy --nginx-config --monitoring"
    echo ""
}

# Функція для розбору аргументів
parse_arguments() {
    SYSTEMD_SERVICE=false
    FIREWALL_SETUP=false
    MONITORING_SETUP=false
    BACKUP_SETUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                SERVER_PORT="$2"
                shift 2
                ;;
            --http-port)
                HTTP_PORT="$2"
                shift 2
                ;;
            --ssl)
                SSL_ENABLED=true
                shift
                ;;
            --ssl-cert)
                SSL_CERT="$2"
                shift 2
                ;;
            --ssl-key)
                SSL_KEY="$2"
                shift 2
                ;;
            --reverse-proxy)
                REVERSE_PROXY=true
                shift
                ;;
            --nginx-config)
                NGINX_CONFIG=true
                shift
                ;;
            --systemd)
                SYSTEMD_SERVICE=true
                shift
                ;;
            --firewall)
                FIREWALL_SETUP=true
                shift
                ;;
            --monitoring)
                MONITORING_SETUP=true
                shift
                ;;
            --backup)
                BACKUP_SETUP=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Невідомий аргумент: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Перевірка SSL параметрів
    if [ "$SSL_ENABLED" = true ]; then
        if [ -z "$SSL_CERT" ] || [ -z "$SSL_KEY" ]; then
            echo -e "${RED}❌ Для SSL потрібні параметри --ssl-cert та --ssl-key${NC}"
            exit 1
        fi
        
        if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
            echo -e "${RED}❌ SSL файли не знайдені: $SSL_CERT, $SSL_KEY${NC}"
            exit 1
        fi
    fi
}

# Функція для перевірки системних вимог
check_system_requirements() {
    echo -e "${YELLOW}🔍 Перевірка системних вимог...${NC}"
    
    # Перевірка операційної системи
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        echo -e "${RED}❌ Цей скрипт призначений для Linux${NC}"
        exit 1
    fi
    
    # Перевірка прав root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Цей скрипт потребує прав root (sudo)${NC}"
        exit 1
    fi
    
    # Перевірка Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠️  Docker не встановлений, встановлюємо...${NC}"
        install_docker
    fi
    
    # Перевірка Docker Compose
    if ! command -v docker compose &> /dev/null; then
        echo -e "${YELLOW}⚠️  Docker Compose не встановлений, встановлюємо...${NC}"
        install_docker_compose
    fi
    
    echo -e "${GREEN}✅ Системні вимоги виконані${NC}"
}

# Функція для встановлення Docker
install_docker() {
    echo -e "${YELLOW}📦 Встановлення Docker...${NC}"
    
    # Оновлюємо пакети
    apt-get update
    
    # Встановлюємо залежності
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    
    # Додаємо Docker GPG ключ
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Додаємо Docker репозиторій
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Встановлюємо Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Запускаємо Docker
    systemctl start docker
    systemctl enable docker
    
    echo -e "${GREEN}✅ Docker встановлено${NC}"
}

# Функція для встановлення Docker Compose
install_docker_compose() {
    echo -e "${YELLOW}📦 Встановлення Docker Compose...${NC}"
    
    # Завантажуємо Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # Робимо виконуваним
    chmod +x /usr/local/bin/docker-compose
    
    # Створюємо симлінк
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo -e "${GREEN}✅ Docker Compose встановлено${NC}"
}

# Функція для налаштування firewall
setup_firewall() {
    if [ "$FIREWALL_SETUP" != true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}🔥 Налаштування firewall...${NC}"
    
    # Встановлюємо ufw якщо не встановлений
    if ! command -v ufw &> /dev/null; then
        apt-get install -y ufw
    fi
    
    # Скидаємо правила
    ufw --force reset
    
    # Дозволяємо SSH
    ufw allow ssh
    
    # Дозволяємо HTTP
    ufw allow 80/tcp
    
    # Дозволяємо HTTPS
    ufw allow 443/tcp
    
    # Дозволяємо MCP порт
    ufw allow $SERVER_PORT/tcp
    
    # Увімкнуємо firewall
    ufw --force enable
    
    echo -e "${GREEN}✅ Firewall налаштовано${NC}"
}

# Функція для створення systemd сервісу
create_systemd_service() {
    if [ "$SYSTEMD_SERVICE" != true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}⚙️  Створення systemd сервісу...${NC}"
    
    # Визначаємо шлях до проекту
    PROJECT_DIR=$(pwd)
    USER=$(logname)
    
    # Створюємо systemd сервіс
    cat > /etc/systemd/system/qa-mcp-server.service << EOF
[Unit]
Description=QA MCP Server
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
User=$USER
Group=$USER
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    # Перезавантажуємо systemd
    systemctl daemon-reload
    
    # Увімкнуємо сервіс
    systemctl enable qa-mcp-server.service
    
    echo -e "${GREEN}✅ Systemd сервіс створено${NC}"
    echo -e "${YELLOW}💡 Команди для управління:${NC}"
    echo -e "${YELLOW}   systemctl start qa-mcp-server    # Запуск${NC}"
    echo -e "${YELLOW}   systemctl stop qa-mcp-server     # Зупинка${NC}"
    echo -e "${YELLOW}   systemctl status qa-mcp-server   # Статус${NC}"
}

# Функція для налаштування Nginx
setup_nginx() {
    if [ "$NGINX_CONFIG" != true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}🌐 Налаштування Nginx...${NC}"
    
    # Встановлюємо Nginx якщо не встановлений
    if ! command -v nginx &> /dev/null; then
        apt-get install -y nginx
    fi
    
    # Створюємо конфігурацію
    cat > /etc/nginx/sites-available/qa-mcp-server << EOF
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS if SSL enabled
    if (\$ssl_enabled = "true") {
        return 301 https://\$server_name\$request_uri;
    }
    
    location / {
        proxy_pass http://localhost:$HTTP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:$HTTP_PORT/health;
        access_log off;
    }
}

# SSL configuration if enabled
EOF
    
    # Додаємо SSL конфігурацію якщо увімкнено
    if [ "$SSL_ENABLED" = true ]; then
        cat >> /etc/nginx/sites-available/qa-mcp-server << EOF

server {
    listen 443 ssl http2;
    server_name _;
    
    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    location / {
        proxy_pass http://localhost:$HTTP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:$HTTP_PORT/health;
        access_log off;
    }
}
EOF
    fi
    
    # Активуємо сайт
    ln -sf /etc/nginx/sites-available/qa-mcp-server /etc/nginx/sites-enabled/
    
    # Видаляємо default сайт
    rm -f /etc/nginx/sites-enabled/default
    
    # Тестуємо конфігурацію
    nginx -t
    
    # Перезавантажуємо Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    echo -e "${GREEN}✅ Nginx налаштовано${NC}"
}

# Функція для налаштування моніторингу
setup_monitoring() {
    if [ "$MONITORING_SETUP" != true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}📊 Налаштування моніторингу...${NC}"
    
    # Створюємо скрипт моніторингу
    cat > /usr/local/bin/qa-mcp-monitor.sh << 'EOF'
#!/bin/bash
# Моніторинг QA MCP сервера

LOG_FILE="/var/log/qa-mcp-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Функція для логування
log() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

# Перевірка статусу контейнерів
check_containers() {
    if ! docker compose ps | grep -q "qa_mysql.*Up"; then
        log "ERROR: MySQL container is down"
        return 1
    fi
    
    if ! docker compose ps | grep -q "qa_qdrant.*Up"; then
        log "ERROR: Qdrant container is down"
        return 1
    fi
    
    if ! docker compose ps | grep -q "qa_mcp_server.*Up"; then
        log "ERROR: MCP server container is down"
        return 1
    fi
    
    return 0
}

# Перевірка HTTP endpoint
check_http() {
    if ! curl -s --connect-timeout 10 http://localhost:3000/health > /dev/null; then
        log "ERROR: HTTP endpoint is not responding"
        return 1
    fi
    
    return 0
}

# Основна логіка
main() {
    cd /path/to/qa_mcp  # Замініть на реальний шлях
    
    if ! check_containers; then
        log "WARNING: Some containers are down, attempting restart"
        docker compose restart
        sleep 30
        
        if ! check_containers; then
            log "ERROR: Failed to restart containers"
            exit 1
        fi
    fi
    
    if ! check_http; then
        log "WARNING: HTTP endpoint not responding"
    fi
    
    log "INFO: Health check passed"
}

main "$@"
EOF
    
    chmod +x /usr/local/bin/qa-mcp-monitor.sh
    
    # Створюємо cron job для моніторингу
    echo "*/5 * * * * /usr/local/bin/qa-mcp-monitor.sh" | crontab -
    
    echo -e "${GREEN}✅ Моніторинг налаштовано${NC}"
    echo -e "${YELLOW}💡 Логи моніторингу: /var/log/qa-mcp-monitor.log${NC}"
}

# Функція для налаштування бекапів
setup_backups() {
    if [ "$BACKUP_SETUP" != true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}💾 Налаштування автоматичних бекапів...${NC}"
    
    # Створюємо скрипт бекапу
    cat > /usr/local/bin/qa-mcp-backup.sh << 'EOF'
#!/bin/bash
# Автоматичний бекап QA MCP сервера

PROJECT_DIR="/path/to/qa_mcp"  # Замініть на реальний шлях
BACKUP_DIR="/var/backups/qa-mcp"
RETENTION_DAYS=30

# Створюємо директорію бекапів
mkdir -p "$BACKUP_DIR"

# Переходимо в директорію проекту
cd "$PROJECT_DIR"

# Створюємо бекап
./scripts/backup_database.sh "auto_backup_$(date +%Y%m%d_%H%M%S)"

# Видаляємо старі бекапи
find "$BACKUP_DIR" -name "auto_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $(date)"
EOF
    
    chmod +x /usr/local/bin/qa-mcp-backup.sh
    
    # Створюємо cron job для бекапів
    echo "0 2 * * * /usr/local/bin/qa-mcp-backup.sh" | crontab -
    
    echo -e "${GREEN}✅ Автоматичні бекапи налаштовано${NC}"
    echo -e "${YELLOW}💡 Бекапи створюються щодня о 2:00${NC}"
    echo -e "${YELLOW}💡 Зберігаються $RETENTION_DAYS днів${NC}"
}

# Функція для показу статусу
show_status() {
    echo -e "\n${GREEN}📊 Статус продакшн сервера:${NC}"
    
    # Статус Docker контейнерів
    echo -e "${YELLOW}🐳 Docker контейнери:${NC}"
    docker compose ps
    
    # Статус systemd сервісу
    if [ "$SYSTEMD_SERVICE" = true ]; then
        echo -e "\n${YELLOW}⚙️  Systemd сервіс:${NC}"
        systemctl status qa-mcp-server.service --no-pager
    fi
    
    # Статус Nginx
    if [ "$NGINX_CONFIG" = true ]; then
        echo -e "\n${YELLOW}🌐 Nginx:${NC}"
        systemctl status nginx --no-pager
    fi
    
    # Статус firewall
    if [ "$FIREWALL_SETUP" = true ]; then
        echo -e "\n${YELLOW}🔥 Firewall:${NC}"
        ufw status
    fi
    
    # Тест HTTP endpoint
    echo -e "\n${YELLOW}🔍 Тест HTTP endpoint:${NC}"
    if curl -s http://localhost:$HTTP_PORT/health > /dev/null; then
        echo -e "${GREEN}✅ HTTP endpoint працює${NC}"
    else
        echo -e "${RED}❌ HTTP endpoint не працює${NC}"
    fi
}

# Основна логіка
main() {
    echo -e "${GREEN}🔧 QA MCP Server - Production Server Setup${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    
    # Обробляємо аргументи
    parse_arguments "$@"
    
    echo -e "${YELLOW}📋 Параметри налаштування:${NC}"
    echo -e "${YELLOW}   Порт сервера: $SERVER_PORT${NC}"
    echo -e "${YELLOW}   HTTP порт: $HTTP_PORT${NC}"
    echo -e "${YELLOW}   SSL: $SSL_ENABLED${NC}"
    echo -e "${YELLOW}   Reverse proxy: $REVERSE_PROXY${NC}"
    echo -e "${YELLOW}   Systemd сервіс: $SYSTEMD_SERVICE${NC}"
    echo -e "${YELLOW}   Firewall: $FIREWALL_SETUP${NC}"
    echo -e "${YELLOW}   Моніторинг: $MONITORING_SETUP${NC}"
    echo -e "${YELLOW}   Бекапи: $BACKUP_SETUP${NC}"
    
    # Перевіряємо системні вимоги
    check_system_requirements
    
    # Налаштовуємо компоненти
    setup_firewall
    create_systemd_service
    setup_nginx
    setup_monitoring
    setup_backups
    
    # Показуємо статус
    show_status
    
    echo -e "\n${GREEN}✅ Продакшн сервер налаштовано!${NC}"
    echo -e "${YELLOW}💡 Наступні кроки:${NC}"
    echo -e "${YELLOW}   1. Відредагуйте .env файл з продакшн налаштуваннями${NC}"
    echo -e "${YELLOW}   2. Запустіть сервіси: systemctl start qa-mcp-server${NC}"
    echo -e "${YELLOW}   3. Перевірте логи: journalctl -u qa-mcp-server -f${NC}"
    echo -e "${YELLOW}   4. Налаштуйте клієнтські підключення${NC}"
}

# Запуск
main "$@"
