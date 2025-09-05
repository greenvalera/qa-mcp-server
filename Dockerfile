FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY mcp_server.py ./

# Set environment variables
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# FastMCP server runs on stdio (no port needed for MCP)
# Port 3000 removed as we're using FastMCP with stdio transport

# Health check for FastMCP server (check if process can start)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.mcp_server; print('FastMCP server can import successfully')" || exit 1

# Default command - FastMCP server with stdio transport
CMD ["python", "-m", "app.mcp_server"]
