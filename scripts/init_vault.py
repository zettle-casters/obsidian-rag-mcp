#!/usr/bin/env python3
"""Script to initialize the knowledge base from an Obsidian vault."""

import argparse
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from obsidian_rag_mcp.config import settings
from obsidian_retriever.manager import KnowledgeBaseManager


def main():
    parser = argparse.ArgumentParser(
        description="Initialize the knowledge base from an Obsidian vault"
    )
    parser.add_argument(
        "vault_path",
        help="Path to the Obsidian vault ZIP file or directory",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help="Paths to include (e.g., 'Notes/' 'Projects/')",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Paths to exclude (e.g., '.obsidian/' 'Templates/')",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Maximum chunk size in characters (default: 500)",
    )

    args = parser.parse_args()

    print(f"Connecting to Neo4j: {settings.neo4j_url}")
    print(f"Connecting to Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")

    manager = KnowledgeBaseManager(
        db_url=settings.neo4j_url,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        prefer_grpc=settings.qdrant_prefer_grpc,
        model_name=settings.embeddings_model
    )

    vault_path = Path(args.vault_path)

    if vault_path.suffix == ".zip":
        print(f"Initializing from ZIP: {vault_path}")
        manager.init_vault_from_zip(
            str(vault_path),
            include_paths=args.include,
            exclude_paths=args.exclude,
            max_chunk_size=args.chunk_size,
        )
    else:
        # For directory, we need to zip it first or use a different method
        print(f"Error: Currently only ZIP files are supported.")
        print(f"Please create a ZIP of your vault: zip -r vault.zip /path/to/vault")
        sys.exit(1)

    print("Initialization complete!")


if __name__ == "__main__":
    main()
