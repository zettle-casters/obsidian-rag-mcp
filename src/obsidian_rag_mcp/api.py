"""FastAPI application with /agent endpoint for Obsidian RAG."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent import run_agent, get_agent
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize agent on startup."""
    # Initialize agent
    get_agent()
    yield


app = FastAPI(
    title="Obsidian RAG Agent",
    description="RAG agent for querying Obsidian knowledge base",
    version="0.1.0",
    lifespan=lifespan,
)


class AgentRequest(BaseModel):
    """Request model for the agent endpoint."""

    query: str
    thread_id: str | None = None


class AgentResponse(BaseModel):
    """Response model for the agent endpoint."""

    query: str
    reformulated_query: str
    answer: str
    notes_used: int
    max_depth_reached: int
    thread_id: str


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/agent", response_model=AgentResponse)
async def agent_endpoint(request: AgentRequest):
    """
    Query the Obsidian RAG agent.

    The agent will:
    1. Reformulate the query for better search
    2. Search for relevant notes
    3. Check if context is sufficient
    4. Recursively extend context by exploring linked notes if needed
    5. Generate a final answer based on accumulated knowledge
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        result = await run_agent(request.query, thread_id)
        return AgentResponse(
            query=result["query"],
            reformulated_query=result["reformulated_query"],
            answer=result["answer"],
            notes_used=result["notes_used"],
            max_depth_reached=result["max_depth_reached"],
            thread_id=thread_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stream")
async def agent_stream_endpoint(request: AgentRequest):
    """
    Stream the agent's progress as it processes the query.

    Returns Server-Sent Events with status updates.
    """
    import json

    thread_id = request.thread_id or str(uuid.uuid4())

    async def generate():
        agent = get_agent()

        initial_state = {
            "original_query": request.query,
            "reformulated_query": "",
            "search_results": [],
            "knowledge_base": [],
            "notes_to_explore": [],
            "explored_notes": set(),
            "current_depth": 0,
            "final_answer": "",
            "status": "started",
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Stream through the graph
        async for event in agent.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                # Serialize the event (handle sets)
                serializable_output = {}
                for k, v in node_output.items():
                    if isinstance(v, set):
                        serializable_output[k] = list(v)
                    else:
                        serializable_output[k] = v

                yield f"data: {json.dumps({'node': node_name, 'output': serializable_output}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'status': 'complete', 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def main():
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "obsidian_rag_mcp.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
