#!/bin/bash
# Скрипт для відновлення баз даних з архіву (MySQL + Qdrant)
# Використання: ./scripts/restore_database.sh <backup_archive.tar.gz>

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
    echo -e "${GREEN}🔧 QA MCP Server - Database Restore Tool${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    echo ""
    echo "Використання: $0 <backup_archive.tar.gz> [options]"
    echo ""
    echo "Параметри:"
    echo "  backup_archive.tar.gz  - Шлях до архіву бекапу"
    echo ""
    echo "Опції:"
    echo "  --force                - Примусове відновлення (видаляє існуючі дані)"
    echo "  --mysql-only           - Відновити тільки MySQL"
    echo "  --qdrant-only          - Відновити тільки Qdrant"
    echo "  --dry-run              - Показати що буде зроблено без виконання"
    echo "  --help                 - Показати цю довідку"
    echo ""
    echo "Приклади:"
    echo "  $0 backups/qa_backup_20241201_120000.tar.gz"
    echo "  $0 backups/qa_backup_20241201_120000.tar.gz --force"
    echo "  $0 backups/qa_backup_20241201_120000.tar.gz --mysql-only"
    echo ""
}

# Функція для перевірки аргументів
check_arguments() {
    if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        show_help
        exit 0
    fi
    
    BACKUP_ARCHIVE="$1"
    
    if [ ! -f "$BACKUP_ARCHIVE" ]; then
        echo -e "${RED}❌ Архів не знайдено: $BACKUP_ARCHIVE${NC}"
        echo -e "${YELLOW}💡 Перевірте шлях до файлу або створіть бекап спочатку${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}📁 Архів знайдено: $BACKUP_ARCHIVE${NC}"
}

# Функція для розбору опцій
parse_options() {
    FORCE_RESTORE=false
    MYSQL_ONLY=false
    QDRANT_ONLY=false
    DRY_RUN=false
    
    shift # Пропускаємо перший аргумент (шлях до архіву)
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                FORCE_RESTORE=true
                shift
                ;;
            --mysql-only)
                MYSQL_ONLY=true
                shift
                ;;
            --qdrant-only)
                QDRANT_ONLY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                echo -e "${RED}❌ Невідома опція: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Перевірка конфліктуючих опцій
    if [ "$MYSQL_ONLY" = true ] && [ "$QDRANT_ONLY" = true ]; then
        echo -e "${RED}❌ Не можна використовувати --mysql-only та --qdrant-only одночасно${NC}"
        exit 1
    fi
}

# Функція для підтвердження дії
confirm_action() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN MODE - нічого не буде змінено${NC}"
        return 0
    fi
    
    if [ "$FORCE_RESTORE" = true ]; then
        echo -e "${YELLOW}⚠️  FORCE MODE - існуючі дані будуть видалені!${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  УВАГА: Ця операція видалить всі існуючі дані в базах!${NC}"
    echo -e "${YELLOW}Продовжити? (y/N): ${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Операцію скасовано${NC}"
        exit 0
    fi
}

# Функція для розпакування архіву
extract_archive() {
    echo -e "${YELLOW}📦 Розпакування архіву...${NC}"
    
    # Створюємо тимчасову директорію
    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"
    
    # Розпаковуємо архів
    tar -xzf "$BACKUP_ARCHIVE" -C "$RESTORE_DIR"
    
    # Знаходимо розпаковану директорію
    EXTRACTED_DIR=$(find "$RESTORE_DIR" -maxdepth 1 -type d | grep -v "^$RESTORE_DIR$" | head -n1)
    
    if [ -z "$EXTRACTED_DIR" ]; then
        echo -e "${RED}❌ Не вдалося знайти розпаковану директорію!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Архів розпаковано: $EXTRACTED_DIR${NC}"
    
    # Показуємо інформацію про бекап
    if [ -f "$EXTRACTED_DIR/backup_info.json" ]; then
        echo -e "${YELLOW}📋 Інформація про бекап:${NC}"
        cat "$EXTRACTED_DIR/backup_info.json" | python3 -m json.tool 2>/dev/null || cat "$EXTRACTED_DIR/backup_info.json"
    fi
}

# Функція для перевірки статусу контейнерів
check_containers() {
    echo -e "${YELLOW}📋 Перевірка статусу Docker контейнерів...${NC}"
    
    if ! docker compose ps | grep -q "qa_mysql.*Up"; then
        echo -e "${RED}❌ MySQL контейнер не запущений!${NC}"
        echo "Запустіть контейнери: docker compose up -d"
        exit 1
    fi
    
    if ! docker compose ps | grep -q "qa_qdrant.*Up"; then
        echo -e "${RED}❌ Qdrant контейнер не запущений!${NC}"
        echo "Запустіть контейнери: docker compose up -d"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Всі контейнери запущені${NC}"
}

# Функція для відновлення MySQL
restore_mysql() {
    if [ "$QDRANT_ONLY" = true ]; then
        echo -e "${BLUE}⏭️  Пропуск MySQL (--qdrant-only)${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🗄️  Відновлення MySQL...${NC}"
    
    MYSQL_DUMP="$EXTRACTED_DIR/mysql_dump.sql"
    
    if [ ! -f "$MYSQL_DUMP" ]; then
        echo -e "${RED}❌ MySQL дамп не знайдено: $MYSQL_DUMP${NC}"
        exit 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано відновлення MySQL з $MYSQL_DUMP${NC}"
        return 0
    fi
    
    # Очищаємо існуючі дані
    echo -e "${YELLOW}🧹 Очищення існуючих даних MySQL...${NC}"
    docker compose exec -T mysql mysql -u root -proot -e "DROP DATABASE IF EXISTS qa; CREATE DATABASE qa;"
    
    # Відновлюємо дані
    echo -e "${YELLOW}📥 Відновлення даних MySQL...${NC}"
    docker compose exec -T mysql mysql -u root -proot < "$MYSQL_DUMP"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MySQL відновлено успішно${NC}"
    else
        echo -e "${RED}❌ Помилка відновлення MySQL!${NC}"
        exit 1
    fi
}

# Функція для відновлення Qdrant
restore_qdrant() {
    if [ "$MYSQL_ONLY" = true ]; then
        echo -e "${BLUE}⏭️  Пропуск Qdrant (--mysql-only)${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🔍 Відновлення Qdrant...${NC}"
    
    QDRANT_BACKUP="$EXTRACTED_DIR/qdrant_storage.tar.gz"
    
    if [ ! -f "$QDRANT_BACKUP" ]; then
        echo -e "${RED}❌ Qdrant бекап не знайдено: $QDRANT_BACKUP${NC}"
        exit 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}🔍 DRY RUN: Буде виконано відновлення Qdrant з $QDRANT_BACKUP${NC}"
        return 0
    fi
    
    # Зупиняємо Qdrant контейнер
    echo -e "${YELLOW}⏹️  Зупинка Qdrant контейнера...${NC}"
    docker compose stop qdrant
    
    # Очищаємо існуючі дані
    echo -e "${YELLOW}🧹 Очищення існуючих даних Qdrant...${NC}"
    docker volume rm qa_mcp_qdrant_data 2>/dev/null || true
    
    # Запускаємо Qdrant знову
    echo -e "${YELLOW}🚀 Запуск Qdrant контейнера...${NC}"
    docker compose up -d qdrant
    
    # Чекаємо поки Qdrant запуститься
    echo -e "${YELLOW}⏳ Очікування запуску Qdrant...${NC}"
    sleep 10
    
    # Відновлюємо дані
    echo -e "${YELLOW}📥 Відновлення даних Qdrant...${NC}"
    docker compose exec -T qdrant sh -c "cd / && tar -xzf -" < "$QDRANT_BACKUP"
    
    # Перезапускаємо Qdrant для застосування змін
    echo -e "${YELLOW}🔄 Перезапуск Qdrant...${NC}"
    docker compose restart qdrant
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Qdrant відновлено успішно${NC}"
    else
        echo -e "${RED}❌ Помилка відновлення Qdrant!${NC}"
        exit 1
    fi
}

# Функція для очищення тимчасових файлів
cleanup() {
    echo -e "${YELLOW}🧹 Очищення тимчасових файлів...${NC}"
    rm -rf "$RESTORE_DIR"
    echo -e "${GREEN}✅ Очищення завершено${NC}"
}

# Функція для показу статистики
show_statistics() {
    echo -e "\n${GREEN}📊 Статистика відновлення:${NC}"
    echo -e "${YELLOW}Архів: $BACKUP_ARCHIVE${NC}"
    echo -e "${YELLOW}Дата відновлення: $(date)${NC}"
    
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}Статус: Відновлено успішно${NC}"
    else
        echo -e "${YELLOW}Статус: Dry run (не виконано)${NC}"
    fi
}

# Основна логіка
main() {
    echo -e "${GREEN}🔧 QA MCP Server - Database Restore Tool${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    
    # Перевіряємо наявність docker-compose
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker не встановлений!${NC}"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose не встановлений!${NC}"
        exit 1
    fi
    
    # Обробляємо аргументи
    check_arguments "$@"
    parse_options "$@"
    
    # Підтверджуємо дію
    confirm_action
    
    # Виконуємо відновлення
    extract_archive
    check_containers
    restore_mysql
    restore_qdrant
    show_statistics
    
    # Очищаємо тимчасові файли
    cleanup
    
    echo -e "\n${GREEN}✅ Відновлення завершено успішно!${NC}"
    
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}💡 Рекомендації:${NC}"
        echo -e "${YELLOW}   1. Перевірте статус сервісів: docker compose ps${NC}"
        echo -e "${YELLOW}   2. Перевірте логи: docker compose logs${NC}"
        echo -e "${YELLOW}   3. Протестуйте MCP сервер: python3 mcp_server.py${NC}"
    fi
}

# Запуск
main "$@"
