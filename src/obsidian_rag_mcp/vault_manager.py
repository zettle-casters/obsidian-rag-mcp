"""Vault management with multi-tenant support via UUID."""

import uuid
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from obsidian_retriever.manager import KnowledgeBaseManager

from .config import settings


# Global registry: vault_id -> KnowledgeBaseManager
_vault_managers: dict[str, KnowledgeBaseManager] = {}


def create_vault_manager(vault_id: str) -> KnowledgeBaseManager:
    """Create a new KnowledgeBaseManager for a specific vault."""
    manager = KnowledgeBaseManager(
        db_url=settings.neo4j_url,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        prefer_grpc=settings.qdrant_prefer_grpc,
        model_name=settings.embeddings_model,
    )
    _vault_managers[vault_id] = manager
    return manager


def get_vault_manager(vault_id: str) -> Optional[KnowledgeBaseManager]:
    """Get existing vault manager by ID."""
    return _vault_managers.get(vault_id)


def get_or_create_vault_manager(vault_id: str) -> KnowledgeBaseManager:
    """Get existing manager or create a new one."""
    manager = get_vault_manager(vault_id)
    if manager is None:
        manager = create_vault_manager(vault_id)
    return manager


async def upload_vault(
    zip_file_path: str,
    include_paths: list[str] = None,
    exclude_paths: list[str] = None,
    chunk_size: int = 500,
) -> str:
    """
    Upload and initialize a vault from a ZIP file.

    Returns:
        vault_id: UUID identifier for the uploaded vault
    """
    # Generate unique vault ID
    vault_id = str(uuid.uuid4())

    # Create manager for this vault
    manager = create_vault_manager(vault_id)

    # Initialize vault from ZIP
    include_paths = include_paths or []
    exclude_paths = exclude_paths or []

    manager.init_vault_from_zip(
        zip_path=zip_file_path,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        max_chunk_size=chunk_size,
    )

    return vault_id


def list_vaults() -> list[str]:
    """List all registered vault IDs."""
    return list(_vault_managers.keys())


def delete_vault(vault_id: str) -> bool:
    """Remove a vault from the registry."""
    if vault_id in _vault_managers:
        del _vault_managers[vault_id]
        return True
    return False
