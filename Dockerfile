FROM python:3.13-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy workspace configuration
COPY pyproject.toml uv.lock ./

# Copy all submodules
COPY obsidian-parser ./obsidian-parser
COPY ObsidianRetriever ./ObsidianRetriever
COPY obsidian-rag-api ./obsidian-rag-api

# Copy main entry point
COPY main.py ./

# Sync all dependencies using uv workspace
RUN uv sync --frozen

# Expose ports for Agent API and MCP HTTP Server
EXPOSE 8000 8001

# Run both servers (Agent API on 8000, MCP HTTP on 8001)
CMD ["uv", "run", "python", "main.py", "all"]
