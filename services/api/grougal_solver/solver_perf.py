from __future__ import annotations

import functools
import os
import threading
from collections import OrderedDict
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _enabled() -> bool:
    return os.getenv("GROUGAL_SOLVER_MEMOIZE", "1").strip().lower() not in {"0", "false", "no", "off"}


def _short_repr(value: Any, max_chars: int) -> str | None:
    try:
        text = repr(value)
    except Exception:
        return None
    if len(text) > max_chars:
        return None
    return text


def _fingerprint_self(obj: Any, max_chars: int) -> str | None:
    try:
        data = getattr(obj, "__dict__", None)
        if not isinstance(data, dict):
            return f"{type(obj).__module__}.{type(obj).__qualname__}:{id(obj)}"

        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if key.startswith(("_cache", "_memo", "_perf", "_logger")):
                continue
            if callable(value):
                continue
            cleaned[key] = value

        text = repr(cleaned)
        if len(text) > max_chars:
            return None
        return f"{type(obj).__module__}.{type(obj).__qualname__}:{text}"
    except Exception:
        return None


def solver_memoize(max_entries: int = 4096, max_key_chars: int = 16000) -> Callable[[F], F]:
    """Memoizer for deterministic geometry helpers; bypasses unsafe/huge keys."""
    def decorator(func: F) -> F:
        cache: OrderedDict[str, Any] = OrderedDict()
        lock = threading.RLock()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _enabled():
                return func(*args, **kwargs)

            key_parts: list[str] = [func.__module__, func.__qualname__]
            remaining = max_key_chars
            try:
                for index, arg in enumerate(args):
                    if index == 0 and hasattr(arg, "__dict__"):
                        part = _fingerprint_self(arg, max(1000, remaining // 2))
                    else:
                        part = _short_repr(arg, max(1000, remaining // 2))
                    if part is None:
                        return func(*args, **kwargs)
                    remaining -= len(part)
                    if remaining <= 0:
                        return func(*args, **kwargs)
                    key_parts.append(part)

                if kwargs:
                    kw_part = _short_repr(sorted(kwargs.items()), max(1000, remaining))
                    if kw_part is None:
                        return func(*args, **kwargs)
                    key_parts.append(kw_part)
                key = "\x1f".join(key_parts)
            except Exception:
                return func(*args, **kwargs)

            with lock:
                if key in cache:
                    cache.move_to_end(key)
                    return cache[key]

            result = func(*args, **kwargs)

            with lock:
                cache[key] = result
                cache.move_to_end(key)
                while len(cache) > max_entries:
                    cache.popitem(last=False)
            return result

        return wrapper  # type: ignore[return-value]
    return decorator
