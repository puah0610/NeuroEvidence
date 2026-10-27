from contextlib import contextmanager
from typing import Any

try:
    from langfuse import get_client, observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

    def get_client():
        return None


@contextmanager
def null_span():
    yield None


def start_span(client: Any = None, name: str = "span", as_type: str = "span"):
    """Safely start a nested Langfuse observation span if Langfuse client is active."""
    c = client or get_client()
    if c:
        try:
            return c.start_as_current_observation(name=name, as_type=as_type)
        except Exception:
            pass
    return null_span()
