# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

WORKDIR /app

ENV UV_CACHE_DIR=/root/.cache/uv

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy project configuration
COPY obsidian-rag-api/pyproject.toml obsidian-rag-api/uv.lock ./
COPY obsidian-rag-api/pyproject.toml obsidian-rag-api/uv.lock ./obsidian-rag-api/

# Copy minimal package markers to maximize cache hits
COPY obsidian-rag-api/src/obsidian_rag_api/__init__.py obsidian-rag-api/src/obsidian_rag_api/py.typed ./src/obsidian_rag_api/
COPY obsidian-rag-api/src/obsidian_parser/__init__.py obsidian-rag-api/src/obsidian_parser/py.typed ./src/obsidian_parser/
COPY obsidian-rag-api/src/obsidian_retriever/__init__.py obsidian-rag-api/src/obsidian_retriever/py.typed ./src/obsidian_retriever/
COPY obsidian-rag-api/src/obsidian_rag_api/__init__.py obsidian-rag-api/src/obsidian_rag_api/py.typed ./obsidian-rag-api/src/obsidian_rag_api/
COPY obsidian-rag-api/src/obsidian_parser/__init__.py obsidian-rag-api/src/obsidian_parser/py.typed ./obsidian-rag-api/src/obsidian_parser/
COPY obsidian-rag-api/src/obsidian_retriever/__init__.py obsidian-rag-api/src/obsidian_retriever/py.typed ./obsidian-rag-api/src/obsidian_retriever/

# Sync dependencies
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Copy backend sources
COPY obsidian-rag-api/src ./src
COPY obsidian-rag-api/alembic.ini ./alembic.ini
COPY obsidian-rag-api/alembic ./alembic
COPY obsidian-rag-api/README.md ./README.md

# Copy main entry point
COPY main.py ./

# Create directory for persistent data (vaults metadata)
RUN mkdir -p /app/data

# Expose ports for Agent API and MCP HTTP Server
EXPOSE 8000 8001

# Run both servers (Agent API on 8000, MCP HTTP on 8001)
CMD ["uv", "run", "python", "main.py", "all"]
