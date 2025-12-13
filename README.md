# Obsidian RAG MCP

RAG-система для работы с Obsidian-хранилищами знаний через MCP (Model Context Protocol) и интеллектуального агента.

## Что это?

Система позволяет задавать вопросы к вашей базе знаний в Obsidian и получать точные ответы, используя:
- **Семантический поиск** — находит релевантные заметки по смыслу, а не по ключевым словам
- **Граф связей** — учитывает wiki-ссылки между заметками для расширения контекста
- **Рекурсивное расширение контекста** — агент автоматически подтягивает связанные заметки, если информации недостаточно

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         Obsidian Vault                          │
│                    (markdown файлы + ссылки)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ObsidianRetriever                          │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │     Neo4j       │              │     Qdrant      │          │
│  │  (граф связей)  │              │ (векторный поиск)│          │
│  └─────────────────┘              └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────────┐
│      MCP Server           │   │      LangGraph Agent          │
│  (stdio / HTTP транспорт) │   │      (POST /agent)            │
│                           │   │                               │
│  Tools:                   │   │  Граф состояний:              │
│  • read_note              │   │  reformulate → search →       │
│  • search                 │   │  check_context ⟷ extend →    │
│  • extend_context         │   │  generate_answer              │
└───────────────────────────┘   └───────────────────────────────┘
```

## MCP Server

MCP (Model Context Protocol) — протокол для интеграции внешних инструментов с LLM. Сервер предоставляет три инструмента:

### Tools

| Tool | Описание |
|------|----------|
| `read_note` | Читает заметку по ID (путь к файлу). Возвращает полный текст и метаданные |
| `search` | Семантический поиск заметок по запросу. Использует векторные эмбеддинги |
| `extend_context_using_nearest` | Расширяет контекст, проверяя связанные заметки на релевантность |

### Транспорты

- **stdio** — для интеграции с Claude Desktop, Cursor и другими клиентами
- **HTTP** — REST API на порту 8001 для кастомных интеграций

## LangGraph Agent

Агент построен на [LangGraph](https://github.com/langchain-ai/langgraph) 1.x и реализует умный RAG с рекурсивным расширением контекста.

### Граф состояний

```
┌─────────────┐
│    START    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ reformulate │  ← Переформулирует запрос для лучшего поиска
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   search    │  ← Ищет top-K релевантных заметок
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  check_context   │◄────────────────────┐
└────────┬─────────┘                     │
         │                               │
    ┌────┴────┐                          │
    │         │                          │
достаточно  недостаточно                 │
    │         │                          │
    │         ▼                          │
    │  ┌──────────────┐                  │
    │  │extend_context│  ← Проверяет связанные заметки
    │  └──────┬───────┘    параллельно через LLM
    │         │                          │
    │         └──────────────────────────┘
    │              (до max_depth)
    ▼
┌─────────────────┐
│ generate_answer │  ← Генерирует финальный ответ
└────────┬────────┘
         │
         ▼
┌─────────────┐
│     END     │
└─────────────┘
```

### Как работает extend_context

1. Для текущих заметок собираются все связанные (wiki-ссылки, входящие/исходящие)
2. Параллельно для каждой связанной заметки запускается LLM-проверка: "Содержит ли эта заметка информацию для ответа на вопрос?"
3. Релевантные заметки добавляются в базу знаний
4. Процесс повторяется до достижения `MAX_RECURSION_DEPTH` или пока контекст не станет достаточным

### State

```python
class AgentState(TypedDict):
    original_query: str           # Исходный вопрос
    reformulated_query: str       # Переформулированный запрос
    search_results: list[dict]    # Результаты поиска
    knowledge_base: list[Note]    # Накопленные знания
    explored_notes: set[str]      # Уже просмотренные заметки
    current_depth: int            # Текущая глубина рекурсии
    final_answer: str             # Итоговый ответ
```

## Локальный деплой

### Требования

- Docker + Docker Compose
- OpenAI API ключ (или совместимый API)

### 1. Клонирование

```bash
git clone --recursive <repo-url>
cd obsidian-rag-mcp
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_CHEAP_MODEL=gpt-4o-mini  # Для проверок релевантности
MAX_RECURSION_DEPTH=3
SEARCH_TOP_K=5
```

### 3. Подготовка Obsidian Vault

```bash
# Создайте ZIP из вашего vault
cd /path/to/your/ObsidianVault
zip -r vault.zip .

# Переместите в проект
mv vault.zip /path/to/obsidian-rag-mcp/vault/
```

### 4. Запуск

```bash
docker-compose up -d --build
```

**Сервисы:**

| Сервис        | Порт | Назначение              |
|---------------|------|-------------------------|
| Neo4j Browser | 7474 | UI для просмотра графа  |
| Neo4j Bolt    | 7687 | API графовой БД         |
| Qdrant        | 6333 | Векторный поиск         |
| Agent API     | 8000 | REST API агента         |
| MCP HTTP      | 8001 | MCP сервер              |

### 5. Инициализация базы знаний

```bash
docker compose exec obsidian-rag uv run python scripts/init_vault.py \
  /app/vault/vault.zip \
  --exclude ".obsidian/" "Templates/"
```

Опции:
- `--include` — пути для включения
- `--exclude` — пути для исключения
- `--chunk-size` — размер чанка (по умолчанию 500)

### 6. Проверка

```bash
# Health check
curl http://localhost:8000/health

# Тестовый запрос
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum mechanics?"}'
```

## API

### POST /agent

Основной endpoint для запросов к агенту.

**Request:**
```json
{
  "query": "Расскажи про машинное обучение",
  "thread_id": "optional-session-id"
}
```

**Response:**
```json
{
  "query": "Расскажи про машинное обучение",
  "reformulated_query": "machine learning algorithms neural networks deep learning",
  "answer": "На основе ваших заметок...",
  "notes_used": 5,
  "max_depth_reached": 2,
  "thread_id": "abc123"
}
```

### POST /agent/stream

SSE endpoint для стриминга прогресса агента.

### MCP HTTP: POST /mcp

JSON-RPC endpoint для MCP протокола.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "quantum physics", "top_k": 5}
  }
}
```

## Интеграция с Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian-rag": {
      "command": "docker",
      "args": ["compose", "exec", "-T", "obsidian-rag", "uv", "run", "python", "main.py", "mcp"]
    }
  }
}
```

Или для HTTP транспорта используйте URL: `http://localhost:8001/mcp`

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OPENAI_API_KEY` | — | API ключ OpenAI |
| `OPENAI_MODEL` | gpt-4o-mini | Модель для генерации ответов |
| `OPENAI_CHEAP_MODEL` | gpt-4o-mini | Модель для проверок релевантности |
| `MAX_RECURSION_DEPTH` | 3 | Макс. глубина расширения контекста |
| `SEARCH_TOP_K` | 5 | Количество результатов поиска |

## Структура проекта

```
obsidian-rag-mcp/
├── src/obsidian_rag_mcp/
│   ├── __init__.py
│   ├── config.py          # Настройки из ENV
│   ├── llm.py             # LLM утилиты
│   ├── server.py          # MCP Server (stdio)
│   ├── server_http.py     # MCP Server (HTTP)
│   ├── agent.py           # LangGraph агент
│   └── api.py             # FastAPI endpoints
├── scripts/
│   └── init_vault.py      # Инициализация vault
├── ObsidianRetriever/     # Субмодуль: управление знаниями
├── obsidian-parser/       # Субмодуль: парсер markdown
├── vault/                 # Obsidian vault (ZIP)
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Технологии

- **LangChain 1.x** / **LangGraph 1.x** — оркестрация LLM
- **Neo4j** — графовая БД для связей между заметками
- **Qdrant** — векторная БД для семантического поиска
- **FastAPI** — REST API
- **MCP** — Model Context Protocol
- **sentence-transformers** — эмбеддинги (all-MiniLM-L6-v2)

## Лицензия

MIT
