from decimal import Decimal
from typing import Dict

from services.ai.pricing.base import AIModelPrice
from services.ai.pricing.registry import AIPricingRegistry


OPENAI_PROVIDER = "openai"


OPENAI_MODEL_ALIASES: Dict[str, str] = {
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5-mini-2025-08-07": "gpt-5-mini",
}


OPENAI_PRICES = (
    AIModelPrice(
        provider=OPENAI_PROVIDER,
        model="gpt-5-mini",
        input_usd_per_million_tokens=Decimal("0.25"),
        output_usd_per_million_tokens=Decimal("2.00"),
    ),
)


def normalize_openai_model(model: str) -> str:
    normalized = model.strip().lower()

    return OPENAI_MODEL_ALIASES.get(
        normalized,
        normalized,
    )


def create_openai_pricing_registry() -> AIPricingRegistry:
    registry = AIPricingRegistry()

    for price in OPENAI_PRICES:
        registry.register(price)

        for alias, canonical_model in OPENAI_MODEL_ALIASES.items():
            if canonical_model != price.model:
                continue

            registry.register(
                AIModelPrice(
                    provider=price.provider,
                    model=alias,
                    input_usd_per_million_tokens=(
                        price.input_usd_per_million_tokens
                    ),
                    output_usd_per_million_tokens=(
                        price.output_usd_per_million_tokens
                    ),
                )
            )

    return registry
