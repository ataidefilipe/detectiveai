"""
Managed client wrapper for TypeSafe AI (Jev / System One).

Provides a long-lived cached TypeSafeClient for HTTP connection pooling,
version-pinned model defaults, and safe fallback-friendly evaluation.
"""
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from typesafe_sdk import (
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeClient,
    TypeSafeError,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client_cache: dict[tuple[str, str, float, int], TypeSafeClient] = {}


@dataclass(frozen=True)
class SystemOneEvaluation:
    """Normalized result of a System One call with latency and fallback metadata."""

    ok: bool
    response: Optional[Any] = None
    latency_ms: int = 0
    model: str = ""
    error: Optional[str] = None
    fallback_reason: Optional[str] = None


def resolve_typesafe_api_key(api_key: Optional[str] = None) -> str:
    """Resolves the TypeSafe API key from explicit arg, Settings, or environment."""
    return (api_key or settings.TYPESAFE_API_KEY or os.getenv("TYPESAFE_API_KEY", "")).strip()


def reset_typesafe_client_cache() -> None:
    """Closes and clears cached TypeSafeClient instances (primarily for tests)."""
    with _client_lock:
        for client in _client_cache.values():
            try:
                client.close()
            except Exception:
                pass
        _client_cache.clear()


def get_typesafe_client(
    api_key: Optional[str] = None,
    *,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> Optional[TypeSafeClient]:
    """
    Returns a cached, long-lived TypeSafeClient instance for connection pooling.
    Returns None if no API key is configured.
    """
    resolved_key = resolve_typesafe_api_key(api_key)
    if not resolved_key:
        return None

    resolved_model = model or settings.JEV_MODEL
    resolved_timeout = float(timeout if timeout is not None else settings.JEV_TIMEOUT_SECONDS)
    resolved_retries = int(max_retries if max_retries is not None else settings.JEV_MAX_RETRIES)

    cache_key = (resolved_key, resolved_model, resolved_timeout, resolved_retries)

    with _client_lock:
        cached = _client_cache.get(cache_key)
        if cached is not None:
            return cached

        client = TypeSafeClient(
            api_key=resolved_key,
            model=resolved_model,
            timeout=resolved_timeout,
            retry=RetryPolicy(max_retries=resolved_retries, timeout=resolved_timeout),
        )
        _client_cache[cache_key] = client
        return client


def evaluate_system_one(
    state: Any,
    questions: Mapping[str, Any],
    *,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    api_key: Optional[str] = None,
) -> SystemOneEvaluation:
    """
    Executes a System One call against Jev, returning structured latency and
    fallback metadata instead of raising on network/timeout failures.
    """
    resolved_model = model or settings.JEV_MODEL
    client = get_typesafe_client(api_key=api_key, model=resolved_model, timeout=timeout)
    if client is None:
        return SystemOneEvaluation(
            ok=False,
            model=resolved_model,
            error="TYPESAFE_API_KEY not configured",
            fallback_reason="missing_api_key",
        )

    start = time.perf_counter()
    try:
        call_kwargs: dict[str, Any] = {"model": resolved_model}
        if timeout is not None:
            call_kwargs["timeout"] = timeout

        response = client.system_one(state=state, questions=questions, **call_kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return SystemOneEvaluation(
            ok=True,
            response=response,
            latency_ms=latency_ms,
            model=getattr(response, "model", resolved_model) or resolved_model,
        )
    except TypeSafeAPITimeoutError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(f"[typesafe] Jev request timed out after {latency_ms}ms: {e}")
        return SystemOneEvaluation(
            ok=False,
            latency_ms=latency_ms,
            model=resolved_model,
            error=str(e),
            fallback_reason="timeout",
        )
    except (TypeSafeAPIConnectionError, TypeSafeError) as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(f"[typesafe] Jev API error after {latency_ms}ms: {e}")
        return SystemOneEvaluation(
            ok=False,
            latency_ms=latency_ms,
            model=resolved_model,
            error=str(e),
            fallback_reason="api_error",
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(f"[typesafe] Unexpected Jev error after {latency_ms}ms: {e}")
        return SystemOneEvaluation(
            ok=False,
            latency_ms=latency_ms,
            model=resolved_model,
            error=str(e),
            fallback_reason="error",
        )
