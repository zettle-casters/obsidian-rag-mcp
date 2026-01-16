# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

WORKDIR /app

ENV UV_CACHE_DIR=/root/.cache/uv

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy workspace configuration
COPY pyproject.toml uv.lock ./

# Copy dependency manifests first to maximize cache hits
COPY obsidian-parser/pyproject.toml obsidian-parser/uv.lock obsidian-parser/README.md ./obsidian-parser/
COPY ObsidianRetriever/pyproject.toml ObsidianRetriever/uv.lock ObsidianRetriever/README.md ./ObsidianRetriever/
COPY obsidian-rag-api/pyproject.toml obsidian-rag-api/uv.lock obsidian-rag-api/README.md ./obsidian-rag-api/
COPY obsidian_rag_tests/pyproject.toml obsidian_rag_tests/README.md ./obsidian_rag_tests/

# Sync all dependencies using uv workspace
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Copy all submodules
COPY obsidian-parser ./obsidian-parser
COPY ObsidianRetriever ./ObsidianRetriever
COPY obsidian-rag-api ./obsidian-rag-api
COPY obsidian_rag_tests ./obsidian_rag_tests

# Copy main entry point
COPY main.py ./

# Create directory for persistent data (vaults metadata)
RUN mkdir -p /app/data

# Expose ports for Agent API and MCP HTTP Server
EXPOSE 8000 8001

# Run both servers (Agent API on 8000, MCP HTTP on 8001)
CMD ["uv", "run", "python", "main.py", "all"]
