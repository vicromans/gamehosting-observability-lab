from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AIBudgetStatus:
    tenant_id: Optional[int]
    monthly_budget_usd: Decimal
    spent_usd: Decimal
    remaining_usd: Decimal
    utilization_percent: Decimal
    allowed: bool
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.monthly_budget_usd < 0:
            raise ValueError("monthly_budget_usd cannot be negative.")

        if self.spent_usd < 0:
            raise ValueError("spent_usd cannot be negative.")

        if self.remaining_usd < 0:
            raise ValueError("remaining_usd cannot be negative.")

        if self.utilization_percent < 0:
            raise ValueError("utilization_percent cannot be negative.")

        if self.allowed and self.reason:
            raise ValueError(
                "An allowed budget decision cannot include a rejection reason."
            )

        if not self.allowed and not self.reason:
            raise ValueError(
                "A rejected budget decision must include a reason."
            )


class AIBudgetManager(ABC):
    @abstractmethod
    def check(
        self,
        *,
        tenant_id: Optional[int],
        monthly_budget_usd: Decimal,
    ) -> AIBudgetStatus:
        """Return the current monthly budget decision."""
