from decimal import Decimal
from typing import Optional

from services.ai.budget.usage_reader import AIMonthlyUsageReader


class MariaDBAIMonthlyUsageReader(AIMonthlyUsageReader):
    """Read current-month AI spending from ai_usage_logs."""

    def get_monthly_spend(
        self,
        *,
        tenant_id: Optional[int],
    ) -> Decimal:
        # Import lazily so generic AI modules remain usable in
        # environments where the MariaDB driver is not installed.
        from database.connection import get_db_connection

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                if tenant_id is None:
                    cursor.execute(
                        """
                        SELECT
                            COALESCE(
                                SUM(estimated_cost_usd),
                                0
                            ) AS spent_usd
                        FROM ai_usage_logs
                        WHERE status = 'success'
                          AND created_at >= DATE_FORMAT(
                              CURRENT_DATE,
                              '%%Y-%%m-01'
                          )
                          AND created_at < (
                              DATE_FORMAT(
                                  CURRENT_DATE,
                                  '%%Y-%%m-01'
                              ) + INTERVAL 1 MONTH
                          )
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            COALESCE(
                                SUM(estimated_cost_usd),
                                0
                            ) AS spent_usd
                        FROM ai_usage_logs
                        WHERE status = 'success'
                          AND tenant_id = %s
                          AND created_at >= DATE_FORMAT(
                              CURRENT_DATE,
                              '%%Y-%%m-01'
                          )
                          AND created_at < (
                              DATE_FORMAT(
                                  CURRENT_DATE,
                                  '%%Y-%%m-01'
                              ) + INTERVAL 1 MONTH
                          )
                        """,
                        (tenant_id,),
                    )

                row = cursor.fetchone()
                value = row["spent_usd"] if row else Decimal("0")

                return Decimal(str(value or 0))
        finally:
            connection.close()
