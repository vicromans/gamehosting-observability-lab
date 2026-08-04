from time import perf_counter
from typing import Dict, Optional

from decimal import Decimal

from services.ai.alerts import AIBudgetAlertService
from services.ai.budget import (
    AIBudgetManager,
    AllowAllAIBudgetManager,
)
from services.ai.config import AIConfig, load_ai_config
from services.ai.fallback import AIFallbackStrategy
from services.ai.pricing import AIPricingProvider
from services.ai.providers import (
    AIChatRequest,
    AIChatResponse,
    AIProvider,
    GeminiProvider,
    OpenAIProvider,
)
from services.ai.usage import (
    AIUsageRecord,
    AIUsageRecorder,
    NullAIUsageRecorder,
)


class AIGatewayError(RuntimeError):
    """Raised when the AI Gateway cannot process a request."""


class AIGatewayDisabledError(AIGatewayError):
    """Raised when an AI request is attempted while AI is disabled."""


class AIBudgetExceededError(AIGatewayError):
    """Raised when the configured monthly AI budget is exhausted."""


class AIGateway:
    def __init__(
        self,
        *,
        config: Optional[AIConfig] = None,
        providers: Optional[Dict[str, AIProvider]] = None,
        usage_recorder: Optional[AIUsageRecorder] = None,
        pricing_provider: Optional[AIPricingProvider] = None,
        budget_manager: Optional[AIBudgetManager] = None,
        alert_service: Optional[AIBudgetAlertService] = None,
        fallback_strategy: Optional[AIFallbackStrategy] = None,
    ) -> None:
        self._config = config or load_ai_config()
        self._providers: Dict[str, AIProvider] = dict(providers or {})
        self._usage_recorder = usage_recorder or NullAIUsageRecorder()
        self._pricing_provider = pricing_provider
        self._budget_manager = (
            budget_manager or AllowAllAIBudgetManager()
        )
        self._alert_service = alert_service
        self._fallback_strategy = fallback_strategy

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

        if self._config.provider == "gemini":
            return GeminiProvider(
                api_key=self._config.gemini_api_key or "",
                model=self._config.gemini_model or "",
            )

        raise AIGatewayError(
            f"No provider factory exists for {self._config.provider!r}."
        )

    def _get_provider(self, provider_name: Optional[str] = None) -> AIProvider:
        provider_name = provider_name or self._config.provider
        provider = self._providers.get(provider_name)

        if provider is None:
            if provider_name != self._config.provider:
                raise AIGatewayError(
                    f"AI fallback provider {provider_name!r} is not configured."
                )

            provider = self._create_configured_provider()
            self._providers[provider_name] = provider

        return provider

    def _provider_order(self):
        if self._fallback_strategy is None:
            return (self._config.provider,)

        return self._fallback_strategy.provider_order(
            primary_provider=self._config.provider,
            available_providers=self._providers.keys(),
        )

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        if not self._config.enabled:
            raise AIGatewayDisabledError(
                "AI Gateway is disabled. Set AI_ENABLED=true to enable it."
            )

        budget_status = self._budget_manager.check(
            tenant_id=request.tenant_id,
            monthly_budget_usd=self._config.monthly_budget_usd,
        )

        if self._alert_service is not None:
            self._alert_service.process(
                status=budget_status,
            )

        if not budget_status.allowed:
            raise AIBudgetExceededError(
                budget_status.reason
                or "Monthly AI budget exceeded."
            )

        provider_order = self._provider_order()

        if not provider_order:
            raise AIGatewayError(
                "No AI providers are available for this request."
            )

        response = None
        successful_latency_ms = 0
        attempt_errors = []

        for provider_name in provider_order:
            provider = self._get_provider(provider_name)
            started_at = perf_counter()

            try:
                response = provider.chat(request)

            except Exception as exc:
                latency_ms = max(
                    0,
                    int((perf_counter() - started_at) * 1000),
                )

                self._usage_recorder.record(
                    AIUsageRecord(
                        tenant_id=request.tenant_id,
                        conversation_id=request.conversation_id,
                        provider=provider.name,
                        model=getattr(
                            provider,
                            "model",
                            provider_name,
                        ),
                        request_id=None,
                        status="error",
                        latency_ms=latency_ms,
                        error_message=str(exc),
                    )
                )

                attempt_errors.append(
                    f"{provider.name}: {exc}"
                )

                continue

            successful_latency_ms = max(
                0,
                int((perf_counter() - started_at) * 1000),
            )

            break

        if response is None:
            details = "; ".join(attempt_errors)

            raise AIGatewayError(
                "All AI providers failed."
                + (
                    f" Attempts: {details}"
                    if details
                    else ""
                )
            )

        latency_ms = successful_latency_ms

        estimated_cost_usd = Decimal("0")

        if self._pricing_provider is not None:
            try:
                price = self._pricing_provider.get_price(
                    provider=response.provider,
                    model=response.model,
                )
                estimated_cost_usd = price.estimate_cost(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
            except LookupError:
                # An unknown or newly versioned model must not discard
                # an otherwise valid AI response. It will be logged at
                # zero cost until its price is registered.
                estimated_cost_usd = Decimal("0")

        self._usage_recorder.record(
            AIUsageRecord(
                tenant_id=request.tenant_id,
                conversation_id=request.conversation_id,
                provider=response.provider,
                model=response.model,
                request_id=response.request_id,
                status="success",
                latency_ms=latency_ms,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                estimated_cost_usd=estimated_cost_usd,
            )
        )

        return response


def create_ai_gateway(
    *,
    config: Optional[AIConfig] = None,
    providers: Optional[Dict[str, AIProvider]] = None,
    usage_recorder: Optional[AIUsageRecorder] = None,
    pricing_provider: Optional[AIPricingProvider] = None,
    budget_manager: Optional[AIBudgetManager] = None,
    alert_service: Optional[AIBudgetAlertService] = None,
    fallback_strategy: Optional[AIFallbackStrategy] = None,
) -> AIGateway:
    return AIGateway(
        config=config,
        providers=providers,
        usage_recorder=usage_recorder,
        pricing_provider=pricing_provider,
        budget_manager=budget_manager,
        alert_service=alert_service,
        fallback_strategy=fallback_strategy,
    )
