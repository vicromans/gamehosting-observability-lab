from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from services.ai.budget.base import (
    AIBudgetManager,
    AIBudgetStatus,
)
from services.ai.budget.policy import AIBudgetPolicyReader
from services.ai.budget.usage_reader import AIMonthlyUsageReader

PERCENT = Decimal("100")
PERCENT_QUANTUM = Decimal("0.01")


class DefaultAIBudgetManager(AIBudgetManager):
    def __init__(
        self,
        usage_reader: AIMonthlyUsageReader,
        policy_reader: Optional[AIBudgetPolicyReader] = None,
    ) -> None:
        self._usage_reader = usage_reader
        self._policy_reader = policy_reader

    def check(
        self,
        *,
        tenant_id: Optional[int],
        monthly_budget_usd: Decimal,
    ) -> AIBudgetStatus:
        effective_budget = monthly_budget_usd
        warning_percent = Decimal("80.00")

        if self._policy_reader is not None:
            policy = self._policy_reader.get_policy(
                tenant_id=tenant_id,
                default_monthly_budget_usd=monthly_budget_usd,
            )

            effective_budget = policy.monthly_budget_usd
            warning_percent = policy.warning_percent

        spent = self._usage_reader.get_monthly_spend(
            tenant_id=tenant_id,
        )

        if effective_budget == 0:
            utilization = Decimal("100.00")
            remaining = Decimal("0")
        else:
            remaining = max(
                Decimal("0"),
                effective_budget - spent,
            )

            utilization = (
                spent
                * PERCENT
                / effective_budget
            ).quantize(
                PERCENT_QUANTUM,
                rounding=ROUND_HALF_UP,
            )

        allowed = spent < effective_budget

        if not allowed:
            level = "exceeded"
        elif utilization >= warning_percent:
            level = "warning"
        else:
            level = "normal"

        return AIBudgetStatus(
            tenant_id=tenant_id,
            monthly_budget_usd=effective_budget,
            spent_usd=spent,
            remaining_usd=remaining,
            utilization_percent=utilization,
            warning_percent=warning_percent,
            level=level,
            allowed=allowed,
            reason=(
                None
                if allowed
                else "Monthly AI budget exceeded."
            ),
        )
