from services.ai.config import (
    AIConfig,
    AIConfigError,
    load_ai_config,
)
from services.ai.gateway import (
    AIBudgetExceededError,
    AIGateway,
    AIGatewayDisabledError,
    AIGatewayError,
    create_ai_gateway,
)
from services.ai.providers import (
    AIChatRequest,
    AIChatResponse,
    AIMessage,
    AIProvider,
    AIUsage,
)

__all__ = [
    "AIConfig",
    "AIConfigError",
    "load_ai_config",
    "AIGateway",
    "AIGatewayDisabledError",
    "AIGatewayError",
    "create_ai_gateway",
    "AIChatRequest",
    "AIChatResponse",
    "AIMessage",
    "AIProvider",
    "AIUsage",
    "create_default_ai_gateway",
]



def __getattr__(name):
    if name == "create_default_ai_gateway":
        from services.ai.factory import create_default_ai_gateway
        return create_default_ai_gateway

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
