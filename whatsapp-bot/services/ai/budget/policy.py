from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AIBudgetPolicy:
    tenant_id: Optional[int]
    monthly_budget_usd: Decimal
    warning_percent: Decimal
    source: str

    def __post_init__(self) -> None:
        if self.monthly_budget_usd < 0:
            raise ValueError(
                "monthly_budget_usd cannot be negative."
            )

        if not Decimal("0") <= self.warning_percent <= Decimal("100"):
            raise ValueError(
                "warning_percent must be between 0 and 100."
            )

        if self.source not in {"tenant", "global"}:
            raise ValueError(
                "Budget policy source must be 'tenant' or 'global'."
            )


class AIBudgetPolicyReader(ABC):
    @abstractmethod
    def get_policy(
        self,
        *,
        tenant_id: Optional[int],
        default_monthly_budget_usd: Decimal,
    ) -> AIBudgetPolicy:
        """Resolve the effective budget policy for one tenant."""
