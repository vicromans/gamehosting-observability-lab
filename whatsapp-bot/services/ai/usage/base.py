from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AIUsageRecord:
    tenant_id: Optional[int]
    conversation_id: Optional[int]
    provider: str
    model: str
    request_id: Optional[str]
    status: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        supported_statuses = {"success", "error"}

        if self.status not in supported_statuses:
            raise ValueError(
                f"Unsupported usage status: {self.status!r}. "
                f"Supported statuses: {', '.join(sorted(supported_statuses))}."
            )

        if not self.provider.strip():
            raise ValueError("Usage provider cannot be empty.")

        if not self.model.strip():
            raise ValueError("Usage model cannot be empty.")

        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative.")

        if min(
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
        ) < 0:
            raise ValueError("Token usage values cannot be negative.")

        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd cannot be negative.")

        if self.status == "success" and self.error_message:
            raise ValueError(
                "Successful usage records cannot include an error message."
            )


class AIUsageRecorder(ABC):
    @abstractmethod
    def record(self, usage: AIUsageRecord) -> None:
        """Persist or emit one AI usage record."""
