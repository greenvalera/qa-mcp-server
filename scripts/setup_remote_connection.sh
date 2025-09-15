#!/bin/bash
# Скрипт для налаштування віддаленого підключення MCP сервера
# Використання: ./scripts/setup_remote_connection.sh [options]

set -e

# Конфігурація
REMOTE_HOST=""
REMOTE_PORT="3000"
CONNECTION_TYPE="http"  # тільки http

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для показу довідки
show_help() {
    echo -e "${GREEN}🔧 QA MCP Server - Remote Connection Setup${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    echo ""
    echo "Використання: $0 [options]"
    echo ""
    echo "Опції:"
    echo "  --host HOST            - Віддалений хост (обов'язково)"
    echo "  --port PORT            - Порт на віддаленому хості (default: 3000)"
    echo "  --type TYPE            - Тип підключення: http (default: http)"
    echo "  --generate-config      - Генерувати конфігурацію для Cursor"
    echo "  --test-connection      - Тестувати підключення"
    echo "  --help                 - Показати цю довідку"
    echo ""
    echo "Типи підключення:"
    echo "  http        - Пряме HTTP підключення (єдиний підтримуваний)"
    echo ""
    echo "Приклади:"
    echo "  $0 --host 192.168.1.100 --type http --generate-config"
    echo "  $0 --host 192.168.1.100 --test-connection"
    echo ""
}

# Функція для розбору аргументів
parse_arguments() {
    GENERATE_CONFIG=false
    TEST_CONNECTION=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                REMOTE_HOST="$2"
                shift 2
                ;;
            --port)
                REMOTE_PORT="$2"
                shift 2
                ;;
            --type)
                CONNECTION_TYPE="$2"
                shift 2
                ;;
            --generate-config)
                GENERATE_CONFIG=true
                shift
                ;;
            --test-connection)
                TEST_CONNECTION=true
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
    
    # Перевірка обов'язкових параметрів
    if [ -z "$REMOTE_HOST" ]; then
        echo -e "${RED}❌ Параметр --host є обов'язковим!${NC}"
        show_help
        exit 1
    fi
    
    # Перевірка типу підключення
    if [ "$CONNECTION_TYPE" != "http" ]; then
        echo -e "${RED}❌ Підтримується тільки HTTP підключення: $CONNECTION_TYPE${NC}"
        echo "Доступний тип: http"
        exit 1
    fi
}

# Функція для тестування підключення
test_connection() {
    echo -e "${YELLOW}🔍 Тестування HTTP підключення до $REMOTE_HOST:$REMOTE_PORT...${NC}"
    test_http_connection
}

# Функція для тестування HTTP підключення
test_http_connection() {
    echo -e "${YELLOW}🌐 Тестування HTTP підключення...${NC}"
    
    # Тестуємо доступність хоста
    if ! ping -c 1 "$REMOTE_HOST" > /dev/null 2>&1; then
        echo -e "${RED}❌ Хост $REMOTE_HOST недоступний${NC}"
        return 1
    fi
    
    # Тестуємо HTTP endpoint
    if curl -s --connect-timeout 10 "http://$REMOTE_HOST:$REMOTE_PORT/health" > /dev/null; then
        echo -e "${GREEN}✅ HTTP підключення працює${NC}"
        
        # Тестуємо JSON-RPC endpoint
        if curl -s --connect-timeout 10 -X POST "http://$REMOTE_HOST:$REMOTE_PORT/jsonrpc" \
           -H "Content-Type: application/json" \
           -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' > /dev/null; then
            echo -e "${GREEN}✅ JSON-RPC endpoint працює${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  JSON-RPC endpoint не відповідає${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ HTTP підключення не працює${NC}"
        return 1
    fi
}


# Функція для генерації конфігурації Cursor
generate_cursor_config() {
    echo -e "${YELLOW}📝 Генерація HTTP конфігурації для Cursor...${NC}"
    
    CURSOR_CONFIG_DIR="$HOME/.cursor"
    CURSOR_CONFIG_FILE="$CURSOR_CONFIG_DIR/mcp.json"
    
    # Створюємо директорію якщо не існує
    mkdir -p "$CURSOR_CONFIG_DIR"
    
    generate_http_config
    
    echo -e "${GREEN}✅ Конфігурація збережена: $CURSOR_CONFIG_FILE${NC}"
    echo -e "${YELLOW}💡 Перезапустіть Cursor для застосування змін${NC}"
}

# Функція для генерації HTTP конфігурації
generate_http_config() {
    cat > "$CURSOR_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "qa-search-remote": {
      "url": "http://$REMOTE_HOST:$REMOTE_PORT/jsonrpc",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
EOF
    
    echo -e "${GREEN}✅ HTTP конфігурація створена${NC}"
    echo -e "${YELLOW}📋 URL: http://$REMOTE_HOST:$REMOTE_PORT/jsonrpc${NC}"
}


# Функція для показу інструкцій
show_instructions() {
    echo -e "\n${GREEN}📋 Інструкції для використання:${NC}"
    
    echo -e "${YELLOW}1. Перезапустіть Cursor${NC}"
    echo -e "${YELLOW}2. Перевірте в Settings → MCP Tools що з'явився 'qa-search-remote'${NC}"
    echo -e "${YELLOW}3. Протестуйте підключення в чаті Cursor${NC}"
    
    echo -e "\n${YELLOW}💡 Корисні команди:${NC}"
    echo -e "${YELLOW}   curl http://$REMOTE_HOST:$REMOTE_PORT/health  # Тест підключення${NC}"
    echo -e "${YELLOW}   ./scripts/setup_remote_connection.sh --host $REMOTE_HOST --test-connection  # Тест${NC}"
}

# Основна логіка
main() {
    echo -e "${GREEN}🔧 QA MCP Server - Remote Connection Setup${NC}"
    echo -e "${YELLOW}==========================================${NC}"
    
    # Обробляємо аргументи
    parse_arguments "$@"
    
    echo -e "${YELLOW}📋 Параметри підключення:${NC}"
    echo -e "${YELLOW}   Хост: $REMOTE_HOST${NC}"
    echo -e "${YELLOW}   Порт: $REMOTE_PORT${NC}"
    echo -e "${YELLOW}   Тип: $CONNECTION_TYPE${NC}"
    
    # Тестуємо підключення якщо потрібно
    if [ "$TEST_CONNECTION" = true ]; then
        test_connection
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Підключення працює${NC}"
        else
            echo -e "${RED}❌ Підключення не працює${NC}"
            exit 1
        fi
    fi
    
    # Генеруємо конфігурацію якщо потрібно
    if [ "$GENERATE_CONFIG" = true ]; then
        generate_cursor_config
        show_instructions
    fi
    
    echo -e "\n${GREEN}✅ Налаштування завершено!${NC}"
}

# Запуск
main "$@"
