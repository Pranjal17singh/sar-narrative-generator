"""LangChain callbacks for audit tracing."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from langchain_core.callbacks import BaseCallbackHandler


class AuditCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler for capturing LLM interactions.

    This handler captures prompts, responses, and retrieval operations
    for audit trail purposes.
    """

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.events: List[Dict[str, Any]] = []
        self.current_run_id: Optional[str] = None
        self.start_time: Optional[datetime] = None

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Capture LLM call start."""
        self.current_run_id = str(run_id)
        self.start_time = datetime.utcnow()

        self.events.append({
            "event_type": "llm_start",
            "run_id": self.current_run_id,
            "timestamp": self.start_time.isoformat(),
            "model": serialized.get("name", "unknown"),
            "prompt_count": len(prompts),
            "prompts": prompts,
        })

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Capture LLM call end."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0

        # Extract response text
        response_text = ""
        if hasattr(response, "generations") and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "text"):
                        response_text += gen.text

        self.events.append({
            "event_type": "llm_end",
            "run_id": str(run_id),
            "timestamp": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "response_length": len(response_text),
            "response": response_text,
        })

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Capture LLM errors."""
        self.events.append({
            "event_type": "llm_error",
            "run_id": str(run_id),
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
        })

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Capture retrieval start."""
        self.events.append({
            "event_type": "retriever_start",
            "run_id": str(run_id),
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
        })

    def on_retriever_end(
        self,
        documents: List[Any],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Capture retrieval results."""
        doc_summaries = []
        for doc in documents:
            if hasattr(doc, "page_content"):
                doc_summaries.append({
                    "content_preview": doc.page_content[:200],
                    "metadata": getattr(doc, "metadata", {}),
                })

        self.events.append({
            "event_type": "retriever_end",
            "run_id": str(run_id),
            "timestamp": datetime.utcnow().isoformat(),
            "document_count": len(documents),
            "documents": doc_summaries,
        })

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all captured events."""
        return self.events

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of captured events."""
        llm_calls = [e for e in self.events if e["event_type"] == "llm_end"]
        retrievals = [e for e in self.events if e["event_type"] == "retriever_end"]
        errors = [e for e in self.events if e["event_type"] == "llm_error"]

        total_duration = sum(e.get("duration_seconds", 0) for e in llm_calls)

        return {
            "case_id": self.case_id,
            "total_events": len(self.events),
            "llm_calls": len(llm_calls),
            "retrieval_operations": len(retrievals),
            "errors": len(errors),
            "total_llm_duration_seconds": round(total_duration, 2),
            "documents_retrieved": sum(e.get("document_count", 0) for e in retrievals),
        }
