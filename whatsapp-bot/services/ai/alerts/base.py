from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class AIBudgetAlert:
    tenant_id: int
    alert_month: date
    level: str
    utilization_percent: Decimal
    spent_usd: Decimal
    monthly_budget_usd: Decimal

    def __post_init__(self) -> None:
        if self.tenant_id <= 0:
            raise ValueError("tenant_id must be positive.")

        if self.level not in {"warning", "exceeded"}:
            raise ValueError(
                "level must be 'warning' or 'exceeded'."
            )

        if self.utilization_percent < 0:
            raise ValueError(
                "utilization_percent cannot be negative."
            )

        if self.spent_usd < 0:
            raise ValueError("spent_usd cannot be negative.")

        if self.monthly_budget_usd < 0:
            raise ValueError(
                "monthly_budget_usd cannot be negative."
            )


class AIBudgetAlertStore(ABC):
    @abstractmethod
    def reserve(self, alert: AIBudgetAlert) -> bool:
        """
        Reserve one alert.

        Return True when this is the first alert for the
        tenant/month/level combination.

        Return False when it already exists.
        """
