"""ChromaDB vector store operations."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.config import get_settings
from backend.rag.embeddings import generate_embeddings, chunk_text

settings = get_settings()

# Global ChromaDB client
_chroma_client = None
_collection = None


def get_chroma_client():
    """Get or initialize ChromaDB client."""
    global _chroma_client

    if _chroma_client is None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            persist_dir = str(settings.vector_store_path)
            Path(persist_dir).mkdir(parents=True, exist_ok=True)

            _chroma_client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            ))
        except Exception as e:
            print(f"Warning: Could not initialize ChromaDB: {e}")
            # Try simpler in-memory client
            try:
                import chromadb
                _chroma_client = chromadb.Client()
            except:
                _chroma_client = None

    return _chroma_client


def get_collection(name: str = "sar_documents"):
    """Get or create a ChromaDB collection."""
    global _collection

    client = get_chroma_client()
    if client is None:
        return None

    try:
        _collection = client.get_or_create_collection(
            name=name,
            metadata={"description": "SAR regulatory documents and templates"},
        )
        return _collection
    except Exception as e:
        print(f"Error getting collection: {e}")
        return None


def add_documents(
    documents: List[str],
    metadatas: List[Dict[str, Any]] = None,
    ids: List[str] = None,
) -> bool:
    """
    Add documents to the vector store.

    Args:
        documents: List of text documents
        metadatas: Optional metadata for each document
        ids: Optional document IDs

    Returns:
        True if successful, False otherwise
    """
    collection = get_collection()
    if collection is None:
        return False

    try:
        # Generate IDs if not provided
        if ids is None:
            import hashlib
            ids = [hashlib.md5(doc.encode()).hexdigest()[:16] for doc in documents]

        # Generate metadata if not provided
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]

        # Add to collection (ChromaDB generates embeddings internally if configured)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        return True

    except Exception as e:
        print(f"Error adding documents: {e}")
        return False


def query_similar(
    query: str,
    n_results: int = None,
) -> List[Dict[str, Any]]:
    """
    Query for similar documents.

    Args:
        query: Query text
        n_results: Number of results to return

    Returns:
        List of matching documents with metadata and scores
    """
    n_results = n_results or settings.top_k_retrieval
    collection = get_collection()

    if collection is None:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        # Format results
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            {
                "content": doc,
                "metadata": meta,
                "distance": dist,
                "similarity": 1 - dist if dist else 1.0,
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    except Exception as e:
        print(f"Error querying vector store: {e}")
        return []


def initialize_vectorstore():
    """
    Initialize vector store with regulatory documents at startup.
    """
    prompts_path = settings.prompts_path

    if not prompts_path.exists():
        print(f"Prompts directory not found: {prompts_path}")
        return

    documents = []
    metadatas = []

    # Load all prompt templates
    for category_dir in prompts_path.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name

        for file_path in category_dir.glob("*.txt"):
            try:
                content = file_path.read_text()
                chunks = chunk_text(content)

                for i, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source": file_path.name,
                        "category": category,
                        "chunk_index": i,
                    })

            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    if documents:
        success = add_documents(documents, metadatas)
        if success:
            print(f"Loaded {len(documents)} document chunks into vector store")
        else:
            print("Failed to load documents into vector store")
    else:
        print("No documents found to load")


def clear_collection(name: str = "sar_documents"):
    """Clear all documents from a collection."""
    client = get_chroma_client()
    if client is None:
        return

    try:
        client.delete_collection(name)
        print(f"Collection '{name}' cleared")
    except Exception as e:
        print(f"Error clearing collection: {e}")
