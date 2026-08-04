from services.ai.budget import (
    DefaultAIBudgetManager,
    MariaDBAIBudgetPolicyReader,
    MariaDBAIMonthlyUsageReader,
)
from services.ai.gateway import AIGateway, create_ai_gateway
from services.ai.pricing import create_openai_pricing_registry
from services.ai.usage import MariaDBAIUsageRecorder


def create_default_ai_gateway() -> AIGateway:
    """Build the production-ready VeldrikLabs AI Gateway."""

    budget_manager = DefaultAIBudgetManager(
        usage_reader=MariaDBAIMonthlyUsageReader(),
        policy_reader=MariaDBAIBudgetPolicyReader(),
    )

    return create_ai_gateway(
        usage_recorder=MariaDBAIUsageRecorder(),
        pricing_provider=create_openai_pricing_registry(),
        budget_manager=budget_manager,
    )
