from typing import Dict, Optional

from services.ai.config import AIConfig, load_ai_config
from services.ai.providers import (
    AIChatRequest,
    AIChatResponse,
    AIProvider,
    OpenAIProvider,
)


class AIGatewayError(RuntimeError):
    """Raised when the AI Gateway cannot process a request."""


class AIGatewayDisabledError(AIGatewayError):
    """Raised when an AI request is attempted while AI is disabled."""


class AIGateway:
    def __init__(
        self,
        *,
        config: Optional[AIConfig] = None,
        providers: Optional[Dict[str, AIProvider]] = None,
    ) -> None:
        self._config = config or load_ai_config()
        self._providers: Dict[str, AIProvider] = dict(providers or {})

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def provider_name(self) -> str:
        return self._config.provider

    @property
    def monthly_budget_usd(self):
        return self._config.monthly_budget_usd

    def _create_configured_provider(self) -> AIProvider:
        if self._config.provider == "openai":
            return OpenAIProvider(
                api_key=self._config.openai_api_key or "",
                model=self._config.openai_model or "",
            )

        raise AIGatewayError(
            f"No provider factory exists for {self._config.provider!r}."
        )

    def _get_provider(self) -> AIProvider:
        provider = self._providers.get(self._config.provider)

        if provider is None:
            provider = self._create_configured_provider()
            self._providers[self._config.provider] = provider

        return provider

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        if not self._config.enabled:
            raise AIGatewayDisabledError(
                "AI Gateway is disabled. Set AI_ENABLED=true to enable it."
            )

        provider = self._get_provider()

        try:
            return provider.chat(request)
        except AIGatewayError:
            raise
        except Exception as exc:
            raise AIGatewayError(
                f"AI provider {provider.name!r} failed: {exc}"
            ) from exc


def create_ai_gateway(
    *,
    config: Optional[AIConfig] = None,
    providers: Optional[Dict[str, AIProvider]] = None,
) -> AIGateway:
    return AIGateway(
        config=config,
        providers=providers,
    )
