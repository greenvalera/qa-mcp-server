#!/bin/bash

# MCP QA Search Server - Quick Start з Mock даними

set -e

echo "🚀 MCP QA Search Server - Quick Start (Mock Data)"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Creating .env file from example..."
    cp env.example .env
    echo "📝 Please edit .env file with your OPENAI_API_KEY before continuing"
    echo "   Run: nano .env"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "❌ OPENAI_API_KEY not found in .env file"
    echo "   Please set your OpenAI API key in .env file"
    echo "   Format: OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

echo "✅ Configuration found"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."

# Check MySQL
if ! docker compose exec -T mysql mysqladmin ping -h localhost --silent; then
    echo "❌ MySQL is not ready yet. Waiting longer..."
    sleep 10
fi

# Check Qdrant
if ! curl -s http://localhost:6333/health >/dev/null 2>&1; then
    echo "❌ Qdrant is not ready yet. Waiting longer..."
    sleep 5
fi

echo "✅ All services are running"

# Create database tables
echo "📋 Creating database tables..."
python3 -c "from app.data.qa_repository import QARepository; QARepository().create_tables()"

# Load mock test data
echo "📚 Loading mock test data from Confluence mock API..."
python3 scripts/confluence/unified_loader.py --use-mock-api --use-config

echo "🧪 Running health check..."
python3 tests/test_mcp_client.py --test health

echo ""
echo "🎉 Setup complete! MCP QA Search Server is ready with mock data."
echo ""
echo "📖 Quick commands:"
echo "   # Full test suite"
echo "   python3 tests/test_mcp_client.py"
echo ""
echo "   # Test MCP server directly"
echo "   echo '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"params\": {\"name\": \"qa_health\", \"arguments\": {}}, \"id\": 1}' | python3 mcp_server.py"
echo ""
echo "   # Health check via HTTP"
echo "   curl http://localhost:3000/health"
echo ""
echo "   # Search test"
echo "   curl -X POST http://localhost:3000/search -H \"Content-Type: application/json\" -d '{\"query\":\"authentication\"}'"
echo ""
echo "   # List features"
echo "   curl http://localhost:3000/features"
echo ""
echo "   # View logs"
echo "   docker compose logs -f mcp-server"
echo ""
echo "   # Stop services"
echo "   docker compose down"
echo ""
echo "🌐 Web interfaces:"
echo "   • MCP Server: http://localhost:3000"
echo "   • Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""
echo "📝 Note: This setup uses MOCK data from Confluence mock API."
echo "   For real Confluence data, use: ./scripts/setup_qa_clean.sh"
echo ""
