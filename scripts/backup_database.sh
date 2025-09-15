#!/bin/bash
# Скрипт для створення архіву баз даних (MySQL + Qdrant)
# Використання: ./scripts/backup_database.sh [backup_name]

set -e

# Конфігурація
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME=${1:-"qa_backup_${TIMESTAMP}"}
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Початок створення архіву баз даних...${NC}"
echo -e "${YELLOW}Назва архіву: ${BACKUP_NAME}${NC}"

# Створюємо директорію для бекапів
mkdir -p "${BACKUP_PATH}"

# Функція для перевірки статусу Docker контейнерів
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

# Функція для створення бекапу MySQL
backup_mysql() {
    echo -e "${YELLOW}🗄️  Створення бекапу MySQL...${NC}"
    
    # Створюємо SQL дамп
    docker compose exec -T mysql mysqldump \
        --user=root \
        --password=root \
        --single-transaction \
        --routines \
        --triggers \
        --all-databases > "${BACKUP_PATH}/mysql_dump.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MySQL бекап створено: ${BACKUP_PATH}/mysql_dump.sql${NC}"
        
        # Показуємо розмір файлу
        DUMP_SIZE=$(du -h "${BACKUP_PATH}/mysql_dump.sql" | cut -f1)
        echo -e "${YELLOW}📊 Розмір MySQL дампу: ${DUMP_SIZE}${NC}"
    else
        echo -e "${RED}❌ Помилка створення MySQL бекапу!${NC}"
        exit 1
    fi
}

# Функція для створення бекапу Qdrant
backup_qdrant() {
    echo -e "${YELLOW}🔍 Створення бекапу Qdrant...${NC}"
    
    # Створюємо директорію для Qdrant бекапу
    mkdir -p "${BACKUP_PATH}/qdrant"
    
    # Копіюємо дані Qdrant з контейнера
    docker compose exec -T qdrant tar -czf - /qdrant/storage > "${BACKUP_PATH}/qdrant_storage.tar.gz"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Qdrant бекап створено: ${BACKUP_PATH}/qdrant_storage.tar.gz${NC}"
        
        # Показуємо розмір файлу
        QDRANT_SIZE=$(du -h "${BACKUP_PATH}/qdrant_storage.tar.gz" | cut -f1)
        echo -e "${YELLOW}📊 Розмір Qdrant бекапу: ${QDRANT_SIZE}${NC}"
    else
        echo -e "${RED}❌ Помилка створення Qdrant бекапу!${NC}"
        exit 1
    fi
}

# Функція для створення метаданих бекапу
create_metadata() {
    echo -e "${YELLOW}📝 Створення метаданих бекапу...${NC}"
    
    cat > "${BACKUP_PATH}/backup_info.json" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "created_by": "$(whoami)",
    "hostname": "$(hostname)",
    "docker_compose_version": "$(docker compose version --short)",
    "mysql_version": "$(docker compose exec mysql mysql --version | cut -d' ' -f3)",
    "qdrant_version": "$(docker compose exec qdrant qdrant --version | head -n1 | cut -d' ' -f2)",
    "backup_size": {
        "mysql_dump": "$(du -b "${BACKUP_PATH}/mysql_dump.sql" | cut -f1)",
        "qdrant_storage": "$(du -b "${BACKUP_PATH}/qdrant_storage.tar.gz" | cut -f1)"
    },
    "description": "QA MCP Server database backup"
}
EOF
    
    echo -e "${GREEN}✅ Метадані створено: ${BACKUP_PATH}/backup_info.json${NC}"
}

# Функція для створення архіву
create_archive() {
    echo -e "${YELLOW}📦 Створення фінального архіву...${NC}"
    
    local original_dir=$(pwd)
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Архів створено: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz${NC}"
        
        # Показуємо розмір архіву
        ARCHIVE_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
        echo -e "${YELLOW}📊 Розмір архіву: ${ARCHIVE_SIZE}${NC}"
        
        # Видаляємо тимчасову директорію
        rm -rf "${BACKUP_NAME}"
        
        echo -e "${GREEN}🎉 Бекап успішно створено!${NC}"
        echo -e "${YELLOW}📁 Шлях до архіву: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz${NC}"
        
        # Повертаємося в оригінальну директорію
        cd "$original_dir"
    else
        echo -e "${RED}❌ Помилка створення архіву!${NC}"
        cd "$original_dir"
        exit 1
    fi
}

# Функція для показу статистики
show_statistics() {
    local archive_file="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    echo -e "\n${GREEN}📊 Статистика бекапу:${NC}"
    echo -e "${YELLOW}Назва: ${BACKUP_NAME}${NC}"
    echo -e "${YELLOW}Дата створення: $(date)${NC}"
    
    if [ -f "$archive_file" ]; then
        echo -e "${YELLOW}Розмір архіву: $(du -h "$archive_file" | cut -f1)${NC}"
        echo -e "${YELLOW}Розташування: $archive_file${NC}"
    else
        echo -e "${RED}❌ Архів не знайдено: $archive_file${NC}"
    fi
}

# Основна логіка
main() {
    echo -e "${GREEN}🔧 QA MCP Server - Database Backup Tool${NC}"
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
    
    # Виконуємо бекап
    check_containers
    backup_mysql
    backup_qdrant
    create_metadata
    create_archive
    show_statistics
    
    echo -e "\n${GREEN}✅ Бекап завершено успішно!${NC}"
    echo -e "${YELLOW}💡 Для відновлення використовуйте: ./scripts/restore_database.sh ${BACKUP_NAME}.tar.gz${NC}"
}

# Запуск
main "$@"
