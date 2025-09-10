#!/bin/bash
# Чистий setup QA системи

set -e

echo "🚀 Чистий setup QA системи..."

# Перевіряємо змінні
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY не встановлений"
    exit 1
fi

if [ -z "$CONFLUENCE_AUTH_TOKEN" ]; then
    echo "❌ CONFLUENCE_AUTH_TOKEN не встановлений"
    exit 1
fi

echo "✅ Змінні середовища встановлені"

# Крок 1: Чиста міграція БД
echo ""
echo "📋 Крок 1: Міграція БД"
python3 -c "from app.data.qa_repository import QARepository; QARepository().create_tables()"

# Крок 2: Тест підключень
echo ""
echo "📋 Крок 2: Тест підключень"
python3 scripts/confluence/unified_loader.py --use-real-api --use-config --test-connection

# Крок 3: Завантаження QA структури (MySQL + Vector DB)
echo ""
echo "📋 Крок 3: Завантаження QA даних в MySQL та векторну базу"
python3 scripts/confluence/unified_loader.py --use-real-api --use-config

# Крок 4: Тест нової системи
echo ""
echo "📋 Крок 4: Тестування системи"
python3 tests/test_mcp_client.py

echo ""
echo "🎉 Чистий QA setup завершено!"
echo ""
echo "📊 Доступні команди:"
echo "  python3 app/mcp_server.py  # Запуск QA MCP сервера"
echo "  python3 scripts/confluence/unified_loader.py --help  # Завантаження даних"
echo "  python3 tests/test_mcp_client.py  # Тестування системи"
