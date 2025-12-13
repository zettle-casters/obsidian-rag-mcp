FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
COPY obsidian-parser ./obsidian-parser
COPY ObsidianRetriever ./ObsidianRetriever

COPY src ./src
COPY scripts ./scripts
COPY main.py ./

RUN uv sync --frozen

EXPOSE 8000 8001

CMD ["uv", "run", "python", "main.py", "all"]
