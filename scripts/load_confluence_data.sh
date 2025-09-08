#!/bin/bash

# Script to load Confluence data using configuration from .env file

echo "📚 Loading Confluence data with current .env configuration..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file based on env.example"
    exit 1
fi

# Load .env file
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Display current configuration
echo "📋 Current configuration:"
echo "  Confluence URL: ${CONFLUENCE_BASE_URL:-not set}"
echo "  Space Key: ${CONFLUENCE_SPACE_KEY:-not set}"
echo "  Root Pages: ${CONFLUENCE_ROOT_PAGES:-not set}"
echo "  OpenAI Model: ${OPENAI_MODEL:-gpt-4.1-mini}"

# Check if required variables are set
if [ -z "$CONFLUENCE_BASE_URL" ] || [ -z "$CONFLUENCE_AUTH_TOKEN" ]; then
    echo "❌ Error: CONFLUENCE_BASE_URL and CONFLUENCE_AUTH_TOKEN must be set in .env file"
    exit 1
fi

# Run the confluence loader
echo "🚀 Starting data load..."
docker compose exec mcp-server python scripts/confluence_loader.py --use-real-api --use-config-pages --once

echo "✅ Data loading completed!"
echo ""
echo "🧪 You can now test the MCP server with the loaded data"
