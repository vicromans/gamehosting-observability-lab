from decimal import Decimal
from typing import Optional

from services.ai.budget.policy import (
    AIBudgetPolicy,
    AIBudgetPolicyReader,
)


DEFAULT_WARNING_PERCENT = Decimal("80.00")


class MariaDBAIBudgetPolicyReader(AIBudgetPolicyReader):
    """Resolve per-tenant AI budget settings from business_settings."""

    def get_policy(
        self,
        *,
        tenant_id: Optional[int],
        default_monthly_budget_usd: Decimal,
    ) -> AIBudgetPolicy:
        if tenant_id is None:
            return AIBudgetPolicy(
                tenant_id=None,
                monthly_budget_usd=default_monthly_budget_usd,
                warning_percent=DEFAULT_WARNING_PERCENT,
                source="global",
            )

        # Lazy import keeps generic AI modules independent of pymysql.
        from database.connection import get_db_connection

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        ai_monthly_budget_usd,
                        ai_budget_warning_percent
                    FROM business_settings
                    WHERE business_id = %s
                    LIMIT 1
                    """,
                    (tenant_id,),
                )

                row = cursor.fetchone()
        finally:
            connection.close()

        if not row:
            return AIBudgetPolicy(
                tenant_id=tenant_id,
                monthly_budget_usd=default_monthly_budget_usd,
                warning_percent=DEFAULT_WARNING_PERCENT,
                source="global",
            )

        tenant_budget = row["ai_monthly_budget_usd"]

        monthly_budget_usd = (
            Decimal(str(tenant_budget))
            if tenant_budget is not None
            else default_monthly_budget_usd
        )

        warning_value = row["ai_budget_warning_percent"]

        warning_percent = (
            Decimal(str(warning_value))
            if warning_value is not None
            else DEFAULT_WARNING_PERCENT
        )

        return AIBudgetPolicy(
            tenant_id=tenant_id,
            monthly_budget_usd=monthly_budget_usd,
            warning_percent=warning_percent,
            source=(
                "tenant"
                if tenant_budget is not None
                else "global"
            ),
        )
