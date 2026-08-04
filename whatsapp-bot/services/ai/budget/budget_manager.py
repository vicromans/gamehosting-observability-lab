from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from services.ai.budget.base import (
    AIBudgetManager,
    AIBudgetStatus,
)
from services.ai.budget.usage_reader import (
    AIMonthlyUsageReader,
)

PERCENT = Decimal("100")
PERCENT_QUANTUM = Decimal("0.01")


class DefaultAIBudgetManager(AIBudgetManager):
    def __init__(
        self,
        usage_reader: AIMonthlyUsageReader,
    ) -> None:
        self._usage_reader = usage_reader

    def check(
        self,
        *,
        tenant_id: Optional[int],
        monthly_budget_usd: Decimal,
    ) -> AIBudgetStatus:

        spent = self._usage_reader.get_monthly_spend(
            tenant_id=tenant_id,
        )

        if monthly_budget_usd == 0:
            utilization = Decimal("100")
            remaining = Decimal("0")
        else:
            remaining = max(
                Decimal("0"),
                monthly_budget_usd - spent,
            )

            utilization = (
                spent
                * PERCENT
                / monthly_budget_usd
            ).quantize(
                PERCENT_QUANTUM,
                rounding=ROUND_HALF_UP,
            )

        allowed = spent < monthly_budget_usd

        return AIBudgetStatus(
            tenant_id=tenant_id,
            monthly_budget_usd=monthly_budget_usd,
            spent_usd=spent,
            remaining_usd=remaining,
            utilization_percent=utilization,
            allowed=allowed,
            reason=(
                None
                if allowed
                else "Monthly AI budget exceeded."
            ),
        )
