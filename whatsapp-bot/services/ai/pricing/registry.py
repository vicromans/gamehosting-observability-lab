from typing import Dict, Iterable, Tuple

from services.ai.pricing.base import (
    AIModelPrice,
    AIPricingProvider,
)


class AIPriceNotFoundError(LookupError):
    """Raised when no price exists for a provider/model pair."""


class AIPricingRegistry(AIPricingProvider):
    def __init__(
        self,
        prices: Iterable[AIModelPrice] = (),
    ) -> None:
        self._prices: Dict[Tuple[str, str], AIModelPrice] = {}

        for price in prices:
            self.register(price)

    @staticmethod
    def _key(provider: str, model: str) -> Tuple[str, str]:
        return (
            provider.strip().lower(),
            model.strip().lower(),
        )

    def register(self, price: AIModelPrice) -> None:
        key = self._key(price.provider, price.model)
        self._prices[key] = price

    def get_price(
        self,
        *,
        provider: str,
        model: str,
    ) -> AIModelPrice:
        key = self._key(provider, model)

        try:
            return self._prices[key]
        except KeyError as exc:
            raise AIPriceNotFoundError(
                "No AI price configured for "
                f"provider={provider!r}, model={model!r}."
            ) from exc

    def estimate_cost(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ):
        price = self.get_price(
            provider=provider,
            model=model,
        )

        return price.estimate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
