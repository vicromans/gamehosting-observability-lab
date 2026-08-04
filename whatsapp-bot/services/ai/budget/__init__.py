from services.ai.budget.allow_all import AllowAllAIBudgetManager
from services.ai.budget.base import (
    AIBudgetManager,
    AIBudgetStatus,
)
from services.ai.budget.budget_manager import DefaultAIBudgetManager
from services.ai.budget.usage_reader import AIMonthlyUsageReader

__all__ = [
    "AIBudgetManager",
    "AIBudgetStatus",
    "AIMonthlyUsageReader",
    "AllowAllAIBudgetManager",
    "MariaDBAIMonthlyUsageReader",
]


def __getattr__(name):
    if name == "MariaDBAIMonthlyUsageReader":
        from services.ai.budget.mariadb_usage_reader import (
            MariaDBAIMonthlyUsageReader,
        )

        return MariaDBAIMonthlyUsageReader

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
