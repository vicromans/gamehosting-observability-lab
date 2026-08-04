import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


class AIConfigError(ValueError):
    """Raised when the AI Gateway configuration is invalid."""


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise AIConfigError(
        f"Invalid boolean value: {value!r}. "
        "Use true/false, yes/no, on/off, or 1/0."
    )


def _parse_non_negative_decimal(
    value: Optional[str],
    *,
    default: str,
    variable_name: str,
) -> Decimal:
    raw_value = default if value is None or not value.strip() else value.strip()

    try:
        parsed_value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise AIConfigError(
            f"{variable_name} must be a valid decimal number."
        ) from exc

    if parsed_value < 0:
        raise AIConfigError(
            f"{variable_name} cannot be negative."
        )

    return parsed_value


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    provider: str
    monthly_budget_usd: Decimal
    openai_api_key: Optional[str]
    openai_model: Optional[str]

    @classmethod
    def from_env(cls) -> "AIConfig":
        enabled = _parse_bool(os.getenv("AI_ENABLED"), default=False)

        provider = os.getenv("AI_PROVIDER", "openai").strip().lower()
        if not provider:
            raise AIConfigError("AI_PROVIDER cannot be empty.")

        monthly_budget_usd = _parse_non_negative_decimal(
            os.getenv("AI_MONTHLY_BUDGET_USD"),
            default="10.00",
            variable_name="AI_MONTHLY_BUDGET_USD",
        )

        config = cls(
            enabled=enabled,
            provider=provider,
            monthly_budget_usd=monthly_budget_usd,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL") or None,
        )

        config.validate()
        return config

    def validate(self) -> None:
        supported_providers = {"openai"}

        if self.provider not in supported_providers:
            raise AIConfigError(
                f"Unsupported AI_PROVIDER: {self.provider!r}. "
                f"Supported providers: {', '.join(sorted(supported_providers))}."
            )

        if not self.enabled:
            return

        if self.provider == "openai":
            if not self.openai_api_key:
                raise AIConfigError(
                    "OPENAI_API_KEY is required when AI_ENABLED=true "
                    "and AI_PROVIDER=openai."
                )

            if not self.openai_model:
                raise AIConfigError(
                    "OPENAI_MODEL is required when AI_ENABLED=true "
                    "and AI_PROVIDER=openai."
                )


def load_ai_config() -> AIConfig:
    return AIConfig.from_env()
