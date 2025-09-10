#!/bin/bash

# Script to reload configuration from .env file and restart services

echo "🔄 Reloading QA MCP configuration from .env file..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file based on env.example"
    exit 1
fi

# Load .env file
echo "📄 Loading environment variables from .env..."
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Display current Confluence configuration
echo "📋 Current Confluence configuration:"
echo "  Base URL: ${CONFLUENCE_BASE_URL:-not set}"
echo "  Space Key: ${CONFLUENCE_SPACE_KEY:-not set}"
echo "  Root Pages: ${CONFLUENCE_ROOT_PAGES:-not set}"
echo "  Auth Token: ${CONFLUENCE_AUTH_TOKEN:+***set***}"

# Restart Docker containers to pick up new environment
echo "🐳 Restarting Docker containers..."
docker compose down
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker compose ps

echo "✅ Configuration reload completed!"
echo ""
echo "🚀 To load data from Confluence with new configuration:"
echo "   docker compose exec mcp-server python scripts/confluence/unified_loader.py --use-real-api --use-config --once"
echo ""
echo "🧪 To test MCP server:"
echo "   Use the MCP tools in your IDE or run test commands"
