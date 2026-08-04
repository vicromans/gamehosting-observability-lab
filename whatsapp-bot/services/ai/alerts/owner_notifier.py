import os
from typing import Optional

from database.connection import get_db_connection
from services.ai.alerts.base import AIBudgetAlert
from services.ai.alerts.service import AIBudgetAlertNotifier
from services.ai.budget import AIBudgetStatus
from services.whatsapp_service import send_whatsapp_message


class OwnerAIBudgetAlertNotifier(AIBudgetAlertNotifier):
    def __init__(
        self,
        *,
        admin_phone_number: Optional[str] = None,
    ) -> None:
        self._admin_phone_number = (
            admin_phone_number
            or os.getenv("VELDRIKLABS_ADMIN_PHONE_NUMBER")
        )

    def _get_business_name(self, tenant_id: int) -> str:
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT business_name
                    FROM businesses
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (tenant_id,),
                )

                row = cursor.fetchone()

                if not row:
                    return f"Tenant {tenant_id}"

                return row["business_name"]

        finally:
            connection.close()

    def build_message(
        self,
        *,
        alert: AIBudgetAlert,
        status: AIBudgetStatus,
    ) -> str:
        business_name = self._get_business_name(
            alert.tenant_id
        )

        if alert.level == "warning":
            title = "⚠️ Alerta de presupuesto IA"
            action = (
                "El servicio continúa activo, pero conviene "
                "revisar el consumo."
            )
        else:
            title = "🚨 Presupuesto IA agotado"
            action = (
                "Las nuevas llamadas de IA de este tenant "
                "serán bloqueadas."
            )

        return (
            f"{title}\n\n"
            f"Negocio: {business_name}\n"
            f"Tenant ID: {alert.tenant_id}\n"
            f"Uso: {alert.utilization_percent}%\n"
            f"Gastado: ${alert.spent_usd} USD\n"
            f"Presupuesto: ${alert.monthly_budget_usd} USD\n"
            f"Nivel: {alert.level}\n\n"
            f"{action}"
        )

    def notify(
        self,
        *,
        alert: AIBudgetAlert,
        status: AIBudgetStatus,
    ) -> None:
        if not self._admin_phone_number:
            raise RuntimeError(
                "VELDRIKLABS_ADMIN_PHONE_NUMBER is not configured."
            )

        message = self.build_message(
            alert=alert,
            status=status,
        )

        send_whatsapp_message(
            self._admin_phone_number,
            message,
            os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            os.getenv("WHATSAPP_TOKEN"),
        )
