from decimal import Decimal
from typing import Optional

from services.ai.budget.base import (
    AIBudgetManager,
    AIBudgetStatus,
)


class AllowAllAIBudgetManager(AIBudgetManager):
    """Budget manager that never blocks an AI request."""

    def check(
        self,
        *,
        tenant_id: Optional[int],
        monthly_budget_usd: Decimal,
    ) -> AIBudgetStatus:
        return AIBudgetStatus(
            tenant_id=tenant_id,
            monthly_budget_usd=monthly_budget_usd,
            spent_usd=Decimal("0"),
            remaining_usd=monthly_budget_usd,
            utilization_percent=Decimal("0"),
            warning_percent=Decimal("80.00"),
            level="normal",
            allowed=True,
        )
