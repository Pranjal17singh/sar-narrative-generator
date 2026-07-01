"""LangChain callback handlers for audit logging."""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid
import hashlib

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult, AgentAction, AgentFinish
from langchain.schema.messages import BaseMessage


class AuditCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for logging LangChain operations to audit trail.

    Captures prompts, responses, and metadata for compliance tracking.
    """

    def __init__(self, audit_id: str):
        """
        Initialize the audit callback handler.

        Args:
            audit_id: The audit ID to associate logs with
        """
        super().__init__()
        self.audit_id = audit_id
        self.run_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Captured data
        self.prompts: List[str] = []
        self.responses: List[str] = []
        self.tokens_used: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        self.model_name: Optional[str] = None
        self.errors: List[str] = []
        self.retrieved_docs: List[Dict[str, Any]] = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        self.run_id = str(run_id)
        self.start_time = datetime.utcnow()
        self.prompts.extend(prompts)

        # Extract model name
        if serialized:
            self.model_name = serialized.get("kwargs", {}).get("model", "unknown")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes running."""
        self.end_time = datetime.utcnow()

        # Extract response text
        for generations in response.generations:
            for gen in generations:
                self.responses.append(gen.text)

        # Extract token usage if available
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            self.tokens_used["prompt"] = token_usage.get("prompt_tokens", 0)
            self.tokens_used["completion"] = token_usage.get("completion_tokens", 0)
            self.tokens_used["total"] = token_usage.get("total_tokens", 0)

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        self.end_time = datetime.utcnow()
        self.errors.append(str(error))

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain starts running."""
        pass

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain finishes running."""
        pass

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain errors."""
        self.errors.append(f"Chain error: {str(error)}")

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever starts running."""
        pass

    def on_retriever_end(
        self,
        documents: List[Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever finishes running."""
        # Store retrieved document metadata
        for doc in documents:
            doc_info = {
                "content_preview": doc.page_content[:200] if hasattr(doc, 'page_content') else str(doc)[:200],
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {},
            }
            self.retrieved_docs.append(doc_info)

    def on_retriever_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever errors."""
        self.errors.append(f"Retriever error: {str(error)}")

    def get_audit_data(self) -> Dict[str, Any]:
        """
        Get all captured data for audit logging.

        Returns:
            Dictionary containing all captured audit data
        """
        # Calculate duration
        duration_seconds = None
        if self.start_time and self.end_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()

        # Create prompt hash for integrity
        full_prompt = "\n".join(self.prompts)
        prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()

        return {
            "audit_id": self.audit_id,
            "run_id": self.run_id,
            "model_name": self.model_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration_seconds,
            "prompt_hash": prompt_hash,
            "prompt_sent": full_prompt,
            "llm_response": "\n".join(self.responses),
            "tokens_used": self.tokens_used,
            "retrieved_docs": self.retrieved_docs if self.retrieved_docs else None,
            "errors": self.errors if self.errors else None,
            "success": len(self.errors) == 0 and len(self.responses) > 0,
        }

    def reset(self) -> None:
        """Reset the callback handler state for reuse."""
        self.run_id = None
        self.start_time = None
        self.end_time = None
        self.prompts = []
        self.responses = []
        self.tokens_used = {"prompt": 0, "completion": 0, "total": 0}
        self.model_name = None
        self.errors = []
        self.retrieved_docs = []


class MetricsCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for collecting performance metrics.

    Useful for monitoring and optimization.
    """

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.total_tokens = 0
        self.total_duration_seconds = 0.0
        self.error_count = 0
        self._current_start: Optional[datetime] = None

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        self._current_start = datetime.utcnow()
        self.call_count += 1

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes running."""
        if self._current_start:
            duration = (datetime.utcnow() - self._current_start).total_seconds()
            self.total_duration_seconds += duration

        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            self.total_tokens += token_usage.get("total_tokens", 0)

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        self.error_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        avg_duration = (
            self.total_duration_seconds / self.call_count
            if self.call_count > 0
            else 0
        )

        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "total_duration_seconds": self.total_duration_seconds,
            "average_duration_seconds": avg_duration,
            "error_count": self.error_count,
            "success_rate": (
                (self.call_count - self.error_count) / self.call_count
                if self.call_count > 0
                else 0
            ),
        }
