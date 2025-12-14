# Obsidian RAG MCP

RAG-система для работы с Obsidian-хранилищами знаний через MCP (Model Context Protocol) и интеллектуального агента с поддержкой множественных vault'ов.

## Что это?

Система позволяет задавать вопросы к вашей базе знаний в Obsidian и получать точные ответы, используя:
- **Семантический поиск** — находит релевантные заметки по смыслу, а не по ключевым словам
- **Граф связей** — учитывает wiki-ссылки между заметками для расширения контекста
- **Рекурсивное расширение контекста** — агент автоматически подтягивает связанные заметки, если информации недостаточно
- **Множественные vault'ы** — загружайте и работайте с несколькими vault'ами одновременно через UUID

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multiple Obsidian Vaults                     │
│                    (uploaded as ZIP files)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Vault Manager (UUID-based)                   │
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
│  Tools (vault_id):        │   │  Граф состояний:              │
│  • read_note              │   │  reformulate → search →       │
│  • search                 │   │  check_context ⟷ extend →    │
│  • extend_context         │   │  generate_answer              │
└───────────────────────────┘   └───────────────────────────────┘
```

## Быстрый старт

### 1. Запуск инфраструктуры

```bash
# Клонирование
git clone --recursive <repo-url>
cd obsidian-rag-mcp

# Настройка окружения
cp .env.example .env
# Отредактируйте .env, добавьте OPENAI_API_KEY

# Запуск сервисов
docker-compose up -d --build
```

### 2. Загрузка vault

```bash
# Создайте ZIP из вашего Obsidian vault
cd /path/to/your/ObsidianVault
zip -r vault.zip .

# Загрузите через API
curl -X POST http://localhost:8000/upload \
  -F "file=@vault.zip" \
  -F "chunk_size=500"

# Ответ:
# {
#   "vault_id": "550e8400-e29b-41d4-a716-446655440000",
#   "message": "Vault uploaded successfully. Use this vault_id in your queries.",
#   "status": "success"
# }
```

### 3. Задайте вопрос

```bash
# Сохраните vault_id из предыдущего шага
VAULT_ID="550e8400-e29b-41d4-a716-446655440000"

# Запрос к агенту
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Что такое квантовая механика?\",
    \"vault_id\": \"$VAULT_ID\"
  }"
```

## API Endpoints

### POST /upload

Загружает ZIP-архив с Obsidian vault и возвращает уникальный `vault_id`.

**Параметры (multipart/form-data):**
- `file` (required): ZIP файл с vault'ом
- `include_paths` (optional): Пути для включения, разделенные запятыми
- `exclude_paths` (optional): Пути для исключения, разделенные запятыми
- `chunk_size` (optional): Размер чанков (по умолчанию 500)

**Пример:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@vault.zip" \
  -F "exclude_paths=.obsidian/,Templates/" \
  -F "chunk_size=500"
```

**Ответ:**
```json
{
  "vault_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Vault uploaded successfully. Use this vault_id in your queries.",
  "status": "success"
}
```

### GET /vaults

Возвращает список всех загруженных vault'ов.

**Пример:**
```bash
curl http://localhost:8000/vaults
```

**Ответ:**
```json
{
  "vaults": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e9511-f30c-52e5-b827-557766551111"
  ],
  "count": 2
}
```

### POST /agent

Основной endpoint для запросов к агенту для конкретного vault'а.

**Request:**
```json
{
  "query": "Расскажи про машинное обучение",
  "vault_id": "550e8400-e29b-41d4-a716-446655440000",
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
  "thread_id": "abc123",
  "vault_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /agent/stream

SSE endpoint для стриминга прогресса агента.

**Request:**
```json
{
  "query": "Объясни теорему Нётер",
  "vault_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Пример использования:**
```bash
curl -X POST http://localhost:8000/agent/stream \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Что такое преобразования Лоренца?\",
    \"vault_id\": \"$VAULT_ID\"
  }"
```

## MCP Server

MCP (Model Context Protocol) — протокол для интеграции внешних инструментов с LLM. Сервер предоставляет три инструмента:

### Tools

| Tool | Описание | Параметры |
|------|----------|-----------|
| `read_note` | Читает заметку по ID из указанного vault | `vault_id`, `note_id` |
| `search` | Семантический поиск заметок в vault | `vault_id`, `query`, `top_k` |
| `extend_context_using_nearest` | Расширяет контекст связанными заметками | `vault_id`, `note_id`, `query` |

### Примеры использования MCP

#### read_note
```json
{
  "vault_id": "550e8400-e29b-41d4-a716-446655440000",
  "note_id": "Scientific-Notes/Booodaness/Special Relativity/postulates.md"
}
```

#### search
```json
{
  "vault_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "квантовая физика",
  "top_k": 5
}
```

#### extend_context_using_nearest
```json
{
  "vault_id": "550e8400-e29b-41d4-a716-446655440000",
  "note_id": "path/to/note.md",
  "query": "исходный запрос пользователя"
}
```

### Транспорты

- **stdio** — для интеграции с Claude Desktop, Cursor и другими клиентами
- **HTTP** — REST API на порту 8001 для кастомных интеграций

## LangGraph Agent

Агент построен на [LangGraph](https://github.com/langchain-ai/langgraph) и реализует умный RAG с рекурсивным расширением контекста.

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
│   search    │  ← Ищет top-K релевантных заметок в vault
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
    vault_id: str                 # UUID vault'а
    reformulated_query: str       # Переформулированный запрос
    search_results: list[dict]    # Результаты поиска
    knowledge_base: list[Note]    # Накопленные знания
    explored_notes: set[str]      # Уже просмотренные заметки
    current_depth: int            # Текущая глубина рекурсии
    final_answer: str             # Итоговый ответ
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

**Важно:** После загрузки vault через `/upload`, используйте полученный `vault_id` в MCP инструментах.

## Python Example

```python
import requests

# 1. Upload vault
with open('vault.zip', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f},
        data={'chunk_size': 500}
    )
vault_id = response.json()['vault_id']
print(f"Vault ID: {vault_id}")

# 2. Query the agent
response = requests.post(
    'http://localhost:8000/agent',
    json={
        'query': 'Что такое преобразования Лоренца?',
        'vault_id': vault_id
    }
)
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Notes used: {result['notes_used']}")

# 3. List all vaults
response = requests.get('http://localhost:8000/vaults')
print(f"Available vaults: {response.json()['vaults']}")
```

## Локальный деплой

### Требования

- Docker + Docker Compose
- OpenAI API ключ (или совместимый API)

### Настройка окружения

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

### Запуск сервисов

```bash
docker-compose up -d --build
```

**Доступные сервисы:**

| Сервис        | Порт | Назначение              |
|---------------|------|-------------------------|
| Neo4j Browser | 7474 | UI для просмотра графа  |
| Neo4j Bolt    | 7687 | API графовой БД         |
| Qdrant        | 6333 | Векторный поиск         |
| Agent API     | 8000 | REST API агента         |
| MCP HTTP      | 8001 | MCP сервер (опционально)|

### Проверка

```bash
# Health check
curl http://localhost:8000/health

# Upload vault
curl -X POST http://localhost:8000/upload \
  -F "file=@vault.zip"

# Test query (используйте vault_id из предыдущего ответа)
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Test question", "vault_id": "your-vault-id"}'
```

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OPENAI_API_KEY` | — | API ключ OpenAI |
| `OPENAI_BASE_URL` | None | Опциональный base URL для совместимых API |
| `OPENAI_MODEL` | gpt-4o-mini | Модель для генерации ответов |
| `OPENAI_CHEAP_MODEL` | gpt-4o-mini | Модель для проверок релевантности |
| `MAX_RECURSION_DEPTH` | 3 | Макс. глубина расширения контекста |
| `SEARCH_TOP_K` | 5 | Количество результатов поиска |
| `EMBEDDINGS_MODEL` | openai/text-embedding-3-large | Модель для эмбеддингов |

## Структура проекта

```
obsidian-rag-mcp/
├── src/obsidian_rag_mcp/
│   ├── __init__.py
│   ├── config.py          # Настройки из ENV
│   ├── vault_manager.py   # Управление vault'ами через UUID
│   ├── llm.py             # LLM утилиты
│   ├── server.py          # MCP Server (stdio)
│   ├── server_http.py     # MCP Server (HTTP)
│   ├── agent.py           # LangGraph агент с vault_id
│   └── api.py             # FastAPI endpoints + /upload
├── scripts/
│   └── init_vault.py      # Инициализация vault (deprecated)
├── ObsidianRetriever/     # Субмодуль: управление знаниями
├── obsidian-parser/       # Субмодуль: парсер markdown
├── docker-compose.yml
├── Dockerfile
├── USAGE.md               # Подробное руководство
└── pyproject.toml
```

## Важные замечания

1. **Vault persistence**: Загруженные vault'ы хранятся только в памяти приложения. При перезапуске сервера все vault'ы будут потеряны и нужно будет загрузить их заново.

2. **UUID уникальность**: Каждая загрузка создает новый UUID, даже если вы загружаете тот же самый vault.

3. **Кодировка**: Все ответы корректно поддерживают UTF-8, включая кириллицу.

4. **Ограничения**:
   - Поддерживаются только ZIP архивы
   - Максимальная глубина рекурсии по умолчанию: 3
   - Top-K результатов поиска: 5

## Технологии

- **LangChain / LangGraph** — оркестрация LLM
- **Neo4j** — графовая БД для связей между заметками
- **Qdrant** — векторная БД для семантического поиска
- **FastAPI** — REST API
- **MCP** — Model Context Protocol
- **OpenAI embeddings** — text-embedding-3-large

## Дополнительная документация

- [USAGE.md](USAGE.md) — Подробное руководство с примерами

## Лицензия

MIT
