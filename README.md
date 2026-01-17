# Obsidian RAG MCP

RAG-система для работы с Obsidian-хранилищами знаний через MCP (Model Context Protocol) и интеллектуального агента с поддержкой множественных vault'ов.

## Что это?

Система позволяет задавать вопросы к вашей базе знаний в Obsidian и получать точные ответы, используя:
- **Семантический поиск** — находит релевантные заметки по смыслу, а не по ключевым словам
- **Граф связей** — учитывает wiki-ссылки между заметками для расширения контекста
- **Рекурсивное расширение контекста** — агент автоматически подтягивает связанные заметки, если информации недостаточно
- **Множественные vault'ы** — загружайте и работайте с несколькими vault'ами одновременно через UUID
- **Модульная архитектура** — проект разделен на независимые подмодули для гибкого использования

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
# Клонирование с подмодулями (HTTPS или SSH - оба работают!)
git clone --recurse-submodules https://github.com/zettle-casters/obsidian-rag-mcp.git
# Или через SSH: git clone --recurse-submodules git@github.com:zettle-casters/obsidian-rag-mcp.git

cd obsidian-rag-mcp

# Если уже клонировали без --recurse-submodules:
# git submodule update --init --recursive

# Настройка окружения
cp .env.example .env
# Отредактируйте .env, добавьте OPENAI_API_KEY

# Запуск сервисов
docker compose up -d --build
```

### 2. Откройте веб-интерфейс

```bash
# Откройте в браузере
open http://localhost:3000
```

**Веб-интерфейс** предоставляет удобный способ работы:
- 🎯 Drag-and-drop загрузка vault'ов (просто перетащите .zip файл)
- 📊 Визуализация прогресса обработки в реальном времени
- 💬 Интерактивный чат с RAG агентом
- 📁 Просмотр всех загруженных vault'ов

### 3. Использование через веб-интерфейс

1. Создайте ZIP из вашего Obsidian vault:
   ```bash
   cd /path/to/your/ObsidianVault
   zip -r vault.zip .
   ```

2. Перетащите `vault.zip` на главную страницу или нажмите "Загрузить Vault"

3. Дождитесь завершения обработки (прогресс отображается в реальном времени)

4. Выберите загруженное хранилище и начните задавать вопросы!

### Альтернатива: Использование через API

Также можно работать напрямую через REST API:

```bash
# Загрузка vault
curl -X POST http://localhost:8000/upload \
  -F "file=@vault.zip" \
  -F "chunk_size=500"

# Запрос к агенту
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Что такое квантовая механика?\",
    \"vault_id\": \"your-vault-id\"
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

### POST /upload/stream

Загружает ZIP-архив с Obsidian vault и **стримит прогресс** через Server-Sent Events.

**Параметры (multipart/form-data):** такие же как у `/upload`

**Пример:**
```bash
curl -X POST http://localhost:8000/upload/stream \
  -F "file=@vault.zip" \
  -F "chunk_size=500"
```

**Формат событий (SSE):**
```json
data: {"stage": "extracting", "progress": 15, "message": "Extracted 150/1000 files...", "elapsed": "2s", "eta": "11s"}

data: {"stage": "parsing", "progress": 50, "message": "Parsed 42 notes"}

data: {"stage": "processing", "progress": 65, "message": "Processed 20/42 notes...", "elapsed": "5s", "eta": "8s"}

data: {"stage": "storing", "progress": 82, "message": "Stored 35/42 notes...", "elapsed": "45s", "eta": "12s"}

data: {"stage": "linking", "progress": 100, "message": "Link building complete"}

data: {"stage": "complete", "progress": 100, "message": "Vault uploaded successfully", "vault_id": "550e8400-e29b-41d4-a716-446655440000", "notes_count": 42}
```

**Поля в событиях:**
- `stage` - текущий этап (extracting, parsing, processing, storing, linking, complete)
- `progress` - процент завершения (0-100)
- `message` - описание текущей операции
- `elapsed` - время с начала текущего этапа (только для длительных операций)
- `eta` - оценочное время до завершения текущего этапа (только для длительных операций)
- `vault_id` - UUID vault'а (только в финальном сообщении)
- `notes_count` - количество обработанных заметок (только в финальном сообщении)

**Этапы загрузки:**
1. `extracting` (0-30%) - Распаковка ZIP архива
2. `parsing` (30-50%) - Парсинг markdown файлов
3. `initializing` (50-55%) - Создание vault manager
4. `processing` (55-75%) - Обработка заметок и построение графа
5. `storing` (75-90%) - Сохранение в БД (Neo4j + Qdrant)
6. `linking` (90-100%) - Построение связей между заметками
7. `complete` (100%) - Завершение с возвратом `vault_id`

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

MCP (Model Context Protocol) — протокол для интеграции внешних инструментов с LLM. Сервер предоставляет четыре инструмента:

### Tools

| Tool | Описание | Параметры |
|------|----------|-----------|
| `list_vaults` | Возвращает список доступных vault'ов | `query` (опц.), `limit` (опц.) |
| `read_note` | Читает заметку по ID из указанного vault | `vault_id`, `note_id` |
| `search` | Семантический поиск заметок в vault | `vault_id`, `query`, `top_k` |
| `extend_context_using_nearest` | Расширяет контекст связанными заметками | `vault_id`, `note_id`, `query` |

### Примеры использования MCP

Для MCP HTTP используйте заголовок `Authorization: Bearer <MCP_TOKEN>`.

#### list_vaults
```json
{
  "query": "physics",
  "limit": 10
}
```

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

**Авторизация MCP:** для HTTP используйте `Authorization: Bearer <MCP_TOKEN>`, для stdio задайте `MCP_AUTH_TOKEN` в окружении.
Токен можно посмотреть в личном кабинете веб‑интерфейса (раздел MCP доступ).

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
| **Web UI**    | **3000** | **Веб-интерфейс**       |
| Neo4j Browser | 7474 | UI для просмотра графа  |
| Neo4j Bolt    | 7687 | API графовой БД         |
| Qdrant        | 6333 | Векторный поиск         |
| Agent API     | 8000 | REST API агента         |
| MCP HTTP      | 8001 | MCP сервер (опционально)|

### Проверка

```bash
# Откройте веб-интерфейс в браузере
open http://localhost:3000

# Health check API
curl http://localhost:8000/health
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
obsidian-rag-mcp/                    # Главный проект (orchestrator)
├── main.py                          # Entry point для запуска всех компонентов
├── docker-compose.yml               # Docker инфраструктура
├── Dockerfile                       # Контейнер с API и MCP серверами
├── pyproject.toml                   # Python/UV конфигурация
│
├── obsidian-rag-ui/                 # 🖥️  Веб-интерфейс (Next.js)
│   └── ...                          # Next.js + React
│
├── obsidian-rag-api/                # 📦 Подмодуль: API и MCP серверы
│   ├── src/obsidian_rag_api/        # Backend (DDD слои + интерфейсы)
│   ├── src/obsidian_retriever/      # Локальный пакет: Neo4j + Qdrant
│   └── src/obsidian_parser/         # Локальный пакет: парсер Markdown
│   └── pyproject.toml
```

### Компоненты

Проект состоит из следующих компонентов:

1. **obsidian-rag-ui** — Веб-интерфейс на Next.js с минималистичным дизайном (GitHub-style)
   - Drag-and-drop загрузка vault'ов
   - Стриминг прогресса обработки
   - Интерактивный чат с RAG агентом

2. **obsidian-rag-api** — API сервер, MCP серверы и LangGraph агент ([README](./obsidian-rag-api/README.md))

3. **obsidian_retriever** — интеграция с Neo4j и Qdrant (внутри backend)

4. **obsidian_parser** — парсинг markdown файлов Obsidian (внутри backend)

## Важные замечания

1. **Vault persistence**: Загруженные vault'ы хранятся только в памяти приложения. При перезапуске сервера все vault'ы будут потеряны и нужно будет загрузить их заново.

2. **UUID уникальность**: Каждая загрузка создает новый UUID, даже если вы загружаете тот же самый vault.

3. **Кодировка**: Все ответы корректно поддерживают UTF-8, включая кириллицу.

4. **Ограничения**:
   - Поддерживаются только ZIP архивы
   - Максимальная глубина рекурсии по умолчанию: 3
   - Top-K результатов поиска: 5

## Технологии

### Backend
- **LangChain / LangGraph** — оркестрация LLM
- **Neo4j** — графовая БД для связей между заметками
- **Qdrant** — векторная БД для семантического поиска
- **FastAPI** — REST API с поддержкой SSE
- **MCP** — Model Context Protocol
- **OpenAI embeddings** — text-embedding-3-large
- **uv** — современный менеджер пакетов и workspace manager

### Frontend
- **Next.js 15** — React фреймворк
- **TypeScript** — типизация
- **Tailwind CSS** — стилизация
- **shadcn/ui** — UI компоненты
- **Lucide Icons** — иконки

### Infrastructure
- **Docker Compose** — оркестрация сервисов


## Метрики

RAG-система демонстрирует **высокие значения Answer–Query Alignment (4.7/5)** и **Self-Consistency (4.9/5)**, что указывает на корректное понимание запросов и логически связные ответы. **Hallucination Risk остаётся низким (0.23)**, поэтому система в целом не склонна к уверенным неподкреплённым утверждениям, особенно на вопросах вне домена базы знаний.

В то же время **Informational Density (3.3/5)** и **Reasoning Depth Alignment (2.9/5)** находятся на среднем уровне, что говорит о недостаточной глубине рассуждений и избыточной осторожности: ответы часто корректны, но не используют весь reasoning-потенциал системы. **Notes Usage Adequacy (3.0/5)** также указывает на умеренно эффективное, но не оптимальное использование контекста.

Модуль переформулировки работает качественно — **Reformulation Quality (4.7/5)** высокая, однако **Reformulation Risk (0.5)** показывает, что примерно в половине случаев переформулированный запрос добавляет лишние предположения. **Appropriate Uncertainty** проявляется в 60% ответов, что в целом отражает здоровый баланс между осторожностью и полезностью.

**Итог:** система — **надёжный и устойчивый RAG-ассистент** с сильными показателями по Answer–Query Alignment и Self-Consistency и низким Hallucination Risk; основные зоны роста — повышение Informational Density, улучшение Reasoning Depth Alignment и снижение Reformulation Risk.
