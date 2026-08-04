from typing import Iterable, Sequence, Tuple

from services.ai.fallback.base import AIFallbackStrategy


class OrderedAIFallbackStrategy(AIFallbackStrategy):
    def __init__(
        self,
        fallback_providers: Sequence[str] = (),
    ) -> None:
        self._fallback_providers = tuple(
            provider.strip().lower()
            for provider in fallback_providers
            if provider and provider.strip()
        )

    def provider_order(
        self,
        *,
        primary_provider: str,
        available_providers: Iterable[str],
    ) -> Sequence[str]:
        primary = primary_provider.strip().lower()
        available = {
            provider.strip().lower()
            for provider in available_providers
        }

        ordered = []

        if primary in available:
            ordered.append(primary)

        for provider in self._fallback_providers:
            if provider not in available:
                continue

            if provider in ordered:
                continue

            ordered.append(provider)

        return tuple(ordered)
