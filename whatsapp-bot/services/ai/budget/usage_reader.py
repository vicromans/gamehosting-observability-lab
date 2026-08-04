from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional


class AIMonthlyUsageReader(ABC):
    @abstractmethod
    def get_monthly_spend(
        self,
        *,
        tenant_id: Optional[int],
    ) -> Decimal:
        """Return successful estimated AI spending for the current month."""
