from services.ai.alerts.base import (
    AIBudgetAlert,
    AIBudgetAlertStore,
)
from services.ai.alerts.service import (
    AIBudgetAlertNotifier,
    AIBudgetAlertService,
)

__all__ = [
    "AIBudgetAlert",
    "AIBudgetAlertNotifier",
    "AIBudgetAlertService",
    "AIBudgetAlertStore",
    "MariaDBAIBudgetAlertStore",
]


def __getattr__(name):
    if name == "MariaDBAIBudgetAlertStore":
        from services.ai.alerts.mariadb_store import (
            MariaDBAIBudgetAlertStore,
        )

        return MariaDBAIBudgetAlertStore

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
