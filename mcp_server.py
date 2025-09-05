#!/usr/bin/env python3
"""MCP QA Search Server launcher script."""

import os
import sys
import subprocess
from pathlib import Path

# Add the app directory to Python path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.insert(0, str(app_dir))

def main():
    """Launch the MCP server."""
    try:
        # Set environment variables if .env file exists
        env_file = current_dir / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
        
        # Import and run the server
        from app.mcp_server import main as server_main
        server_main()
        
    except ImportError as e:
        # Fallback: try to run the server module directly
        print(f"Import error: {e}", file=sys.stderr)
        print("Trying to run server directly...", file=sys.stderr)
        
        # Change to project directory
        os.chdir(current_dir)
        
        # Run the server using subprocess
        cmd = [sys.executable, "-m", "app.mcp_server"]
        subprocess.run(cmd)
        
    except Exception as e:
        print(f"Failed to start MCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
