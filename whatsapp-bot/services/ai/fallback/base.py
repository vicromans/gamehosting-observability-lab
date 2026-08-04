from abc import ABC, abstractmethod
from typing import Iterable, Sequence


class AIFallbackStrategy(ABC):
    @abstractmethod
    def provider_order(
        self,
        *,
        primary_provider: str,
        available_providers: Iterable[str],
    ) -> Sequence[str]:
        """Return providers in the order they should be attempted."""
