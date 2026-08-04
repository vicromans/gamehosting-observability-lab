from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


USD_QUANTUM = Decimal("0.0000000001")
TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class AIModelPrice:
    provider: str
    model: str
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("Pricing provider cannot be empty.")

        if not self.model.strip():
            raise ValueError("Pricing model cannot be empty.")

        if self.input_usd_per_million_tokens < 0:
            raise ValueError("Input token price cannot be negative.")

        if self.output_usd_per_million_tokens < 0:
            raise ValueError("Output token price cannot be negative.")

    def estimate_cost(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> Decimal:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative.")

        input_cost = (
            Decimal(input_tokens)
            * self.input_usd_per_million_tokens
            / TOKENS_PER_MILLION
        )

        output_cost = (
            Decimal(output_tokens)
            * self.output_usd_per_million_tokens
            / TOKENS_PER_MILLION
        )

        return (input_cost + output_cost).quantize(
            USD_QUANTUM,
            rounding=ROUND_HALF_UP,
        )


class AIPricingProvider(ABC):
    @abstractmethod
    def get_price(
        self,
        *,
        provider: str,
        model: str,
    ) -> AIModelPrice:
        """Return pricing for one provider/model combination."""
