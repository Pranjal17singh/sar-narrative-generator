"""Ollama client wrapper with availability detection."""

from typing import Optional, Dict, Any
import httpx

from backend.config import get_settings

settings = get_settings()

# Cache for Ollama availability
_ollama_available: Optional[bool] = None


def check_ollama_available() -> bool:
    """
    Check if Ollama is available and has the required model.

    Caches result to avoid repeated checks.
    """
    global _ollama_available

    if _ollama_available is not None:
        return _ollama_available

    try:
        # Check if Ollama is running
        response = httpx.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=5.0,
        )

        if response.status_code != 200:
            _ollama_available = False
            return False

        # Check if required model is available
        data = response.json()
        models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]

        _ollama_available = settings.ollama_model in models

        if not _ollama_available:
            print(f"Ollama is running but model '{settings.ollama_model}' not found. "
                  f"Available models: {models}")
            print(f"Run 'ollama pull {settings.ollama_model}' to download the model.")

        return _ollama_available

    except Exception as e:
        print(f"Ollama not available: {e}")
        _ollama_available = False
        return False


def reset_ollama_check():
    """Reset the Ollama availability cache."""
    global _ollama_available
    _ollama_available = None


def generate_completion(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> Optional[str]:
    """
    Generate completion using Ollama with streaming.

    Uses streaming mode to avoid Ollama's internal 3-minute timeout.
    On CPU, generation can take 2-5 minutes for complex prompts.

    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text or None if unavailable
    """
    if not check_ollama_available():
        return None

    try:
        import json
        import time

        # Build the request with streaming enabled
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": True,  # Enable streaming to avoid internal timeout
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        # Debug: print prompt sizes
        prompt_len = len(prompt)
        system_len = len(system_prompt) if system_prompt else 0
        print(f"[DEBUG] Sending to Ollama (streaming) - prompt: {prompt_len} chars, system: {system_len} chars")

        start_time = time.time()

        # Use streaming to collect response chunks
        # This avoids Ollama's internal 3-minute timeout
        response_text = []
        token_count = 0

        with httpx.stream(
            "POST",
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=httpx.Timeout(settings.ollama_timeout, connect=10.0),
        ) as response:
            if response.status_code != 200:
                print(f"Ollama error: {response.status_code}")
                return None

            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            response_text.append(chunk["response"])
                            token_count += 1
                            # Progress indicator every 50 tokens
                            if token_count % 50 == 0:
                                elapsed = time.time() - start_time
                                print(f"[DEBUG] Generated {token_count} tokens in {elapsed:.1f}s...")
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        elapsed = time.time() - start_time
        full_response = "".join(response_text)
        print(f"[DEBUG] Ollama completed in {elapsed:.2f}s ({token_count} tokens, {len(full_response)} chars)")

        return full_response

    except httpx.TimeoutException:
        print(f"Ollama request timed out after {settings.ollama_timeout}s")
        return None
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None


def generate_chat_completion(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> Optional[str]:
    """
    Generate chat completion using Ollama chat API.

    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text or None if unavailable
    """
    if not check_ollama_available():
        return None

    try:
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=settings.ollama_timeout,
        )

        if response.status_code != 200:
            print(f"Ollama chat error: {response.status_code}")
            return None

        data = response.json()
        return data.get("message", {}).get("content", "")

    except Exception as e:
        print(f"Error in chat completion: {e}")
        return None


def get_generation_mode() -> str:
    """Get current generation mode based on Ollama availability."""
    return "llm" if check_ollama_available() else "template"
