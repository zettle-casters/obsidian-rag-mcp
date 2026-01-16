# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

WORKDIR /app

ENV UV_CACHE_DIR=/root/.cache/uv

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy workspace configuration
COPY pyproject.toml uv.lock ./

# Copy all submodules
COPY obsidian-parser ./obsidian-parser
COPY ObsidianRetriever ./ObsidianRetriever
COPY obsidian-rag-api ./obsidian-rag-api
COPY obsidian_rag_tests ./obsidian_rag_tests

# Copy main entry point
COPY main.py ./

# Sync all dependencies using uv workspace
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Create directory for persistent data (vaults metadata)
RUN mkdir -p /app/data

# Expose ports for Agent API and MCP HTTP Server
EXPOSE 8000 8001

# Run both servers (Agent API on 8000, MCP HTTP on 8001)
CMD ["uv", "run", "python", "main.py", "all"]
