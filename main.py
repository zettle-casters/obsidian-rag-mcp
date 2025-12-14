import argparse
from dotenv import load_dotenv


def main():
    """Main entry point with CLI argument parsing."""
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Obsidian RAG MCP Server and Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:"
            "  # Run MCP server with stdio transport\n"
            "  python main.py mcp\n\n"
            "  # Run MCP server with HTTP transport\n"
            "  python main.py mcp --http\n\n"
            "  # Run the RAG agent API\n"
            "  python main.py agent\n\n"
            "  # Run both MCP HTTP and Agent API\n"
            "  python main.py all\n"
        ),
    )

    parser.add_argument(
        "command",
        choices=["mcp", "agent", "all"],
        help="Command to run: mcp (MCP server), agent (Agent API), or all (both)",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP transport for MCP server (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for Agent API (default: 8000). MCP HTTP uses port + 1",
    )

    args = parser.parse_args()

    if args.command == "mcp":
        if args.http:
            from obsidian_rag_api.server_http import main as http_main

            http_main()
        else:
            from obsidian_rag_api.server import main as stdio_main

            stdio_main()

    elif args.command == "agent":
        from obsidian_rag_api.api import main as api_main

        api_main()

    elif args.command == "all":
        # Run both servers concurrently
        import asyncio
        import uvicorn

        async def run_all():
            # Import apps
            from obsidian_rag_api.api import app as agent_app
            from obsidian_rag_api.server_http import app as mcp_app

            # Create server configs
            agent_config = uvicorn.Config(
                agent_app,
                host=args.host,
                port=args.port,
                log_level="info",
            )
            mcp_config = uvicorn.Config(
                mcp_app,
                host=args.host,
                port=args.port + 1,
                log_level="info",
            )

            # Create servers
            agent_server = uvicorn.Server(agent_config)
            mcp_server = uvicorn.Server(mcp_config)

            # Run both
            await asyncio.gather(
                agent_server.serve(),
                mcp_server.serve(),
            )

        asyncio.run(run_all())


if __name__ == "__main__":
    main()
