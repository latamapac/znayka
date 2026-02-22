"""Text processing and indexing service."""
from app.services.text.indexer import TextIndexer, get_text_indexer

__all__ = ["TextIndexer", "get_text_indexer"]
