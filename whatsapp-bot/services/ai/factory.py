from services.ai.alerts import (
    AIBudgetAlertService,
    MariaDBAIBudgetAlertStore,
)
from services.ai.alerts.owner_notifier import (
    OwnerAIBudgetAlertNotifier,
)
from services.ai.budget import (
    DefaultAIBudgetManager,
    MariaDBAIBudgetPolicyReader,
    MariaDBAIMonthlyUsageReader,
)
from services.ai.config import load_ai_config
from services.ai.fallback import OrderedAIFallbackStrategy
from services.ai.gateway import AIGateway, create_ai_gateway
from services.ai.pricing import create_openai_pricing_registry
from services.ai.usage import MariaDBAIUsageRecorder


def create_default_ai_gateway() -> AIGateway:
    """Build the production-ready VeldrikLabs AI Gateway."""

    config = load_ai_config()

    budget_manager = DefaultAIBudgetManager(
        usage_reader=MariaDBAIMonthlyUsageReader(),
        policy_reader=MariaDBAIBudgetPolicyReader(),
    )

    alert_service = AIBudgetAlertService(
        store=MariaDBAIBudgetAlertStore(),
        notifier=OwnerAIBudgetAlertNotifier(),
    )

    fallback_strategy = None

    if config.fallback_providers:
        fallback_strategy = OrderedAIFallbackStrategy(
            fallback_providers=config.fallback_providers,
        )

    return create_ai_gateway(
        config=config,
        usage_recorder=MariaDBAIUsageRecorder(),
        pricing_provider=create_openai_pricing_registry(),
        budget_manager=budget_manager,
        alert_service=alert_service,
        fallback_strategy=fallback_strategy,
    )
