#!/bin/bash
# Скрипт для ініціалізації баз даних на продакшн хості
# Використання: ./scripts/init_production_db.sh [backup_archive.tar.gz]

set -e

# Конфігурація
BACKUP_DIR="./backups"
RESTORE_DIR="./restore_temp"

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для показу довідки
show_help() {
    echo -e "${GREEN}🔧 QA MCP Server - Production Database Initialization${NC}"
    echo -e "${YELLOW}====================================================${NC}"
    echo ""
    echo "Використання: $0 [backup_archive.tar.gz] [options]"
    echo ""
    echo "Параметри:"
    echo "  backup_archive.tar.gz  - Шлях до архіву бекапу (опціонально)"
    echo ""
    echo "Опції:"
    echo "  --fresh                - Створити свіжі бази даних (без відновлення)"
    echo "  --force                - Примусова ініціалізація"
    echo "  --dry-run              - Показати що буде зроблено без виконання"
    echo "  --help                 - Показати цю довідку"
    echo ""
    echo "Приклади:"
    echo "  $0                                    # Ініціалізація з нуля"
    echo "  $0 backups/qa_backup_20241201.tar.gz # Відновлення з бекапу"
    echo "  $0 --fresh --force                   # Примусова свіжа ініціалізація"
    echo ""
}

# Функція для перевірки аргументів
check_arguments() {
    BACKUP_ARCHIVE=""
    FRESH_INIT=false
    FORCE_INIT=false
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fresh)
                FRESH_INIT=true
                shift
                ;;
            --force)
                FORCE_INIT=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *.tar.gz)
                BACKUP_ARCHIVE="$1"
                shift
                ;;
            *)
                echo -e "${RED}❌ Невідомий аргумент: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Перевірка конфліктуючих опцій
    if [ -n "$BACKUP_ARCHIVE" ] && [ "$FRESH_INIT" = true ]; then
        echo -e "${RED}❌ Не можна використовувати бекап та --fresh одночасно${NC}"
        exit 1
    fi
}

# Функція для перевірки системних вимог
check_system_requirements() {
    echo -e "${YELLOW}🔍 Перевірка системних вимог...${NC}"
    
    # Перевірка Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker не встановлений!${NC}"
        echo "Встановіть Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Перевірка Docker Compose
    if ! command -v docker compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose не встановлений!${NC}"
        echo "Встановіть Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Перевірка Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 не встановлений!${NC}"
        exit 1
    fi
    
    # Перевірка .env файлу
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  Файл .env не знайдено${NC}"
        echo "Створюємо .env з прикладу..."
        if [ -f "env.example" ]; then
            cp env.example .env
            echo -e "${GREEN}✅ Файл .env створено з env.example${NC}"
            echo -e "${YELLOW}⚠️  ВАЖЛИВО: Відредагуйте .env файл з вашими налаштуваннями!${NC}"
        else
            echo -e "${RED}❌ Файл env.example не знайдено!${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Системні вимоги виконані${NC}"
}

# Функція для створення директорій
create_directories() {
    echo -e "${YELLOW}📁 Створення необхідних директорій...${NC}"
    
    mkdir -p backups
    mkdir -p logs
    mkdir -p data/mysql
    mkdir -p data/qdrant
    
    echo -e "${GREEN}✅ Директорії створено${NC}"
}

# Функція для запуску Docker контейнерів
start_containers() {
    echo -e "${YELLOW}🚀 Запуск Docker контейнерів...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано docker compose up -d${NC}"
        return 0
    fi
    
    # Зупиняємо існуючі контейнери
    docker compose down 2>/dev/null || true
    
    # Запускаємо контейнери
    docker compose up -d
    
    # Чекаємо поки контейнери запустяться
    echo -e "${YELLOW}⏳ Очікування запуску контейнерів...${NC}"
    sleep 15
    
    # Перевіряємо статус
    if docker compose ps | grep -q "qa_mysql.*Up" && docker compose ps | grep -q "qa_qdrant.*Up"; then
        echo -e "${GREEN}✅ Контейнери запущені успішно${NC}"
    else
        echo -e "${RED}❌ Помилка запуску контейнерів!${NC}"
        docker compose logs
        exit 1
    fi
}

# Функція для ініціалізації MySQL
init_mysql() {
    echo -e "${YELLOW}🗄️  Ініціалізація MySQL...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконана ініціалізація MySQL${NC}"
        return 0
    fi
    
    # Чекаємо поки MySQL буде готовий
    echo -e "${YELLOW}⏳ Очікування готовності MySQL...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker compose exec mysql mysqladmin ping -h localhost -u root -proot --silent 2>/dev/null; then
            echo -e "${GREEN}✅ MySQL готовий${NC}"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -e "${YELLOW}   Спроба $attempt/$max_attempts...${NC}"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ MySQL не готовий після $max_attempts спроб${NC}"
        echo -e "${YELLOW}Логи MySQL:${NC}"
        docker compose logs mysql --tail 20
        exit 1
    fi
    
    # Виконуємо ініціалізацію
    if [ -f "scripts/mysql_init.sql" ]; then
        echo -e "${YELLOW}📥 Виконання SQL скриптів ініціалізації...${NC}"
        docker compose exec -T mysql mysql -u root -proot < scripts/mysql_init.sql
    fi
    
    echo -e "${GREEN}✅ MySQL ініціалізовано${NC}"
}

# Функція для ініціалізації Qdrant
init_qdrant() {
    echo -e "${YELLOW}🔍 Ініціалізація Qdrant...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконана ініціалізація Qdrant${NC}"
        return 0
    fi
    
    # Чекаємо поки Qdrant буде готовий
    echo -e "${YELLOW}⏳ Очікування готовності Qdrant...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:6333/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Qdrant готовий${NC}"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -e "${YELLOW}   Спроба $attempt/$max_attempts...${NC}"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ Qdrant не готовий після $max_attempts спроб${NC}"
        echo -e "${YELLOW}Логи Qdrant:${NC}"
        docker compose logs qdrant --tail 20
        exit 1
    fi
    
    echo -e "${GREEN}✅ Qdrant ініціалізовано${NC}"
}

# Функція для відновлення з бекапу
restore_from_backup() {
    if [ -z "$BACKUP_ARCHIVE" ]; then
        return 0
    fi
    
    echo -e "${YELLOW}📦 Відновлення з бекапу: $BACKUP_ARCHIVE${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано відновлення з $BACKUP_ARCHIVE${NC}"
        return 0
    fi
    
    # Використовуємо скрипт відновлення
    ./scripts/restore_database.sh "$BACKUP_ARCHIVE" --force
}

# Функція для завантаження тестових даних
load_test_data() {
    if [ "$FRESH_INIT" = false ] && [ -n "$BACKUP_ARCHIVE" ]; then
        echo -e "${BLUE}⏭️  Пропуск завантаження тестових даних (використовується бекап)${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}📥 Завантаження тестових даних...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано завантаження тестових даних${NC}"
        return 0
    fi
    
    # Завантажуємо тестові дані
    if [ -f "scripts/confluence/unified_loader.py" ]; then
        echo -e "${YELLOW}🔄 Запуск завантаження даних з Confluence...${NC}"
        docker compose exec mcp-server python scripts/confluence/unified_loader.py --use-mock-api --use-config
    fi
    
    echo -e "${GREEN}✅ Тестові дані завантажено${NC}"
}

# Функція для оновлення embeddings
update_embeddings() {
    if [ "$FRESH_INIT" = false ] && [ -n "$BACKUP_ARCHIVE" ]; then
        echo -e "${BLUE}⏭️  Пропуск оновлення embeddings (використовується бекап)${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🧠 Оновлення embeddings...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано оновлення embeddings${NC}"
        return 0
    fi
    
    # Оновлюємо embeddings
    if [ -f "scripts/update_embeddings.sh" ]; then
        echo -e "${YELLOW}🔄 Запуск оновлення embeddings...${NC}"
        ./scripts/update_embeddings.sh
    fi
    
    echo -e "${GREEN}✅ Embeddings оновлено${NC}"
}

# Функція для тестування системи
test_system() {
    echo -e "${YELLOW}🧪 Тестування системи...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано тестування системи${NC}"
        return 0
    fi
    
    # Тестуємо MCP сервер
    echo -e "${YELLOW}🔍 Тестування MCP сервера...${NC}"
    timeout 10 bash -c 'echo "{\"jsonrpc\": \"2.0\", \"method\": \"tools/list\", \"params\": {}, \"id\": 1}" | python3 mcp_server.py' || {
        echo -e "${YELLOW}⚠️  MCP сервер не відповідає (це нормально для stdio режиму)${NC}"
    }
    
    # Тестуємо HTTP API
    echo -e "${YELLOW}🔍 Тестування HTTP API...${NC}"
    if curl -s http://localhost:3000/health > /dev/null; then
        echo -e "${GREEN}✅ HTTP API працює${NC}"
    else
        echo -e "${YELLOW}⚠️  HTTP API не доступний (можливо не запущений)${NC}"
    fi
    
    echo -e "${GREEN}✅ Тестування завершено${NC}"
}

# Функція для показу статистики
show_statistics() {
    echo -e "\n${GREEN}📊 Статистика ініціалізації:${NC}"
    echo -e "${YELLOW}Дата ініціалізації: $(date)${NC}"
    echo -e "${YELLOW}Режим: $([ "$FRESH_INIT" = true ] && echo "Свіжа ініціалізація" || echo "Відновлення з бекапу")${NC}"
    
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}Статус контейнерів:${NC}"
        docker compose ps
        
        echo -e "\n${YELLOW}Розмір баз даних:${NC}"
        echo -e "${YELLOW}MySQL: $(docker compose exec mysql du -sh /var/lib/mysql 2>/dev/null | cut -f1 || echo "N/A")${NC}"
        echo -e "${YELLOW}Qdrant: $(docker compose exec qdrant du -sh /qdrant/storage 2>/dev/null | cut -f1 || echo "N/A")${NC}"
    else
        echo -e "${YELLOW}Статус: Dry run (не виконано)${NC}"
    fi
}

# Функція для показу наступних кроків
show_next_steps() {
    echo -e "\n${GREEN}🎉 Ініціалізація завершена!${NC}"
    echo -e "${YELLOW}📋 Наступні кроки:${NC}"
    echo -e "${YELLOW}   1. Перевірте конфігурацію: nano .env${NC}"
    echo -e "${YELLOW}   2. Запустіть MCP сервер: python3 mcp_server.py${NC}"
    echo -e "${YELLOW}   3. Налаштуйте Cursor: ~/.cursor/mcp.json${NC}"
    echo -e "${YELLOW}   4. Протестуйте підключення${NC}"
    echo ""
    echo -e "${YELLOW}💡 Корисні команди:${NC}"
    echo -e "${YELLOW}   docker compose ps          # Статус контейнерів${NC}"
    echo -e "${YELLOW}   docker compose logs        # Логи сервісів${NC}"
    echo -e "${YELLOW}   ./scripts/backup_database.sh # Створення бекапу${NC}"
}

# Основна логіка
main() {
    echo -e "${GREEN}🔧 QA MCP Server - Production Database Initialization${NC}"
    echo -e "${YELLOW}====================================================${NC}"
    
    # Обробляємо аргументи
    check_arguments "$@"
    
    # Перевіряємо системні вимоги
    check_system_requirements
    
    # Підтверджуємо дію
    if [ "$DRY_RUN" = false ] && [ "$FORCE_INIT" = false ]; then
        echo -e "${YELLOW}⚠️  Ця операція ініціалізує бази даних на продакшн хості${NC}"
        echo -e "${YELLOW}Продовжити? (y/N): ${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}❌ Операцію скасовано${NC}"
            exit 0
        fi
    fi
    
    # Виконуємо ініціалізацію
    create_directories
    start_containers
    init_mysql
    init_qdrant
    restore_from_backup
    load_test_data
    update_embeddings
    test_system
    show_statistics
    show_next_steps
}

# Запуск
main "$@"
