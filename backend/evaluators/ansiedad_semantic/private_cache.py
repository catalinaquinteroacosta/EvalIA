"""Private lazy anxiety cache. Never imports or accesses the shared cache."""
from pathlib import Path
from backend.evaluators.semantic.em.em_private_cache import (
    LazyPrivateCache, build_cache_key,
)

semantic_cache = LazyPrivateCache(Path(__file__).resolve().parent / 'private' / 'anxiety.sqlite3')


def cached_semantic_operation(*, execute, validate_result, **identity):
    key = build_cache_key(**identity)
    cached = semantic_cache.get(key)
    if cached is not None:
        return validate_result(cached)
    value = validate_result(execute())
    semantic_cache.set(key, value)
    return value


class SemanticCache(LazyPrivateCache):
    """Anxiety-only compatibility adapter with genuinely disabled I/O."""
    def __init__(self, *, path, enabled=True):
        super().__init__(path)
        self.enabled = enabled

    def get(self, key):
        return super().get(key) if self.enabled else None

    def set(self, key, value):
        if self.enabled:
            super().set(key, value)
