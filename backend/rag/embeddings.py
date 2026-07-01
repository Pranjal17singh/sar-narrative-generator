"""Embedding generation for RAG system."""

from typing import List, Optional
from functools import lru_cache

from backend.config import get_settings

settings = get_settings()

# Global embedding model instance
_embedding_model = None


def get_embedding_model():
    """Get or initialize the embedding model."""
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(settings.embedding_model)
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            _embedding_model = None

    return _embedding_model


def generate_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Generate embeddings for a list of texts.

    Returns None if embedding model is not available.
    """
    model = get_embedding_model()

    if model is None:
        return None

    try:
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None


def generate_single_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text."""
    result = generate_embeddings([text])
    return result[0] if result else None


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for period, question mark, or exclamation within last 100 chars
            search_start = max(end - 100, start)
            last_period = text.rfind(".", search_start, end)
            last_question = text.rfind("?", search_start, end)
            last_exclaim = text.rfind("!", search_start, end)
            best_break = max(last_period, last_question, last_exclaim)

            if best_break > start:
                end = best_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def prepare_case_context_for_embedding(
    kyc_data: dict,
    features: dict,
    patterns: list,
) -> str:
    """
    Prepare case context as text for embedding/retrieval.
    """
    parts = []

    # KYC summary
    if kyc_data:
        parts.append(f"Customer: {kyc_data.get('name', 'Unknown')}")
        parts.append(f"Account Type: {kyc_data.get('account_type', 'Unknown')}")
        if kyc_data.get("occupation"):
            parts.append(f"Business: {kyc_data['occupation']}")
        if kyc_data.get("country"):
            parts.append(f"Country: {kyc_data['country']}")

    # Feature summary
    if features:
        parts.append(f"Total Inflow: ${features.get('total_inflow', 0):,.2f}")
        parts.append(f"Total Outflow: ${features.get('total_outflow', 0):,.2f}")
        parts.append(f"Transaction Count: {features.get('transaction_count', 0)}")

        if features.get("cross_border_countries"):
            parts.append(f"International activity: {', '.join(features['cross_border_countries'])}")

    # Pattern summary
    if patterns:
        pattern_names = [p.get("pattern_type", "unknown") for p in patterns]
        parts.append(f"Patterns detected: {', '.join(pattern_names)}")

    return ". ".join(parts)
