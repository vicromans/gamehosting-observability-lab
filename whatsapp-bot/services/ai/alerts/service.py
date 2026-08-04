from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from services.ai.alerts.base import (
    AIBudgetAlert,
    AIBudgetAlertStore,
)
from services.ai.budget import AIBudgetStatus


class AIBudgetAlertNotifier(ABC):
    @abstractmethod
    def notify(
        self,
        *,
        alert: AIBudgetAlert,
        status: AIBudgetStatus,
    ) -> None:
        """Deliver one AI budget alert."""


class AIBudgetAlertService:
    def __init__(
        self,
        *,
        store: AIBudgetAlertStore,
        notifier: AIBudgetAlertNotifier,
    ) -> None:
        self._store = store
        self._notifier = notifier

    def process(
        self,
        *,
        status: AIBudgetStatus,
        alert_month: Optional[date] = None,
    ) -> bool:
        if status.tenant_id is None:
            return False

        if status.level not in {"warning", "exceeded"}:
            return False

        month = alert_month or date.today().replace(day=1)

        alert = AIBudgetAlert(
            tenant_id=status.tenant_id,
            alert_month=month,
            level=status.level,
            utilization_percent=status.utilization_percent,
            spent_usd=status.spent_usd,
            monthly_budget_usd=status.monthly_budget_usd,
        )

        reserved = self._store.reserve(alert)

        if not reserved:
            return False

        self._notifier.notify(
            alert=alert,
            status=status,
        )

        return True
