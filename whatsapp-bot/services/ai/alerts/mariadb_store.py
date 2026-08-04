from pymysql.err import IntegrityError

from database.connection import get_db_connection
from services.ai.alerts.base import (
    AIBudgetAlert,
    AIBudgetAlertStore,
)


class MariaDBAIBudgetAlertStore(AIBudgetAlertStore):
    """Persist and deduplicate monthly AI budget alerts."""

    DUPLICATE_ENTRY_CODE = 1062

    def reserve(self, alert: AIBudgetAlert) -> bool:
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_budget_alerts (
                        tenant_id,
                        alert_month,
                        level,
                        utilization_percent,
                        spent_usd,
                        monthly_budget_usd
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        alert.tenant_id,
                        alert.alert_month,
                        alert.level,
                        alert.utilization_percent,
                        alert.spent_usd,
                        alert.monthly_budget_usd,
                    ),
                )

            connection.commit()
            return True

        except IntegrityError as exc:
            connection.rollback()

            error_code = (
                exc.args[0]
                if exc.args
                else None
            )

            if error_code == self.DUPLICATE_ENTRY_CODE:
                return False

            raise

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()
