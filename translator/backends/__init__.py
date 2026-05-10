"""Translation backend abstraction layer.

Backends:
- mock: offline testing (always available)
- hermes_delegate: parallel subagent translation via delegate_task
- minimax_api: direct MiniMax API fallback
- sequential: single-threaded fallback
"""

from .base import TranslationBackend, BackendResult
from .mock import MockBackend
from .hermes_delegate import HermesDelegateBackend
from .minimax_api import MiniMaxBackend
from .sequential import SequentialBackend
from .sanitizer import sanitize_subagent_output


BACKEND_REGISTRY = {
    "mock": MockBackend,
    "hermes_delegate": HermesDelegateBackend,
    "minimax_api": MiniMaxBackend,
    "sequential": SequentialBackend,
}


def get_backend(name: str, **kwargs) -> TranslationBackend:
    """Factory function to get a backend by name."""
    cls = BACKEND_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown backend: {name}. Available: {list(BACKEND_REGISTRY.keys())}")
    return cls(**kwargs)


def default_backend() -> TranslationBackend:
    """Return the default backend (mock for v1.0)."""
    return MockBackend()