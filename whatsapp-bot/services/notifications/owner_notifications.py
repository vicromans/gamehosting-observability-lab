import os

from database.connection import get_db_connection
from services.whatsapp_service import (
    send_human_support_template_message,
    send_whatsapp_message,
)


OWNER_PHONE_NUMBER = os.getenv("OWNER_PHONE_NUMBER")
DASHBOARD_INBOX_URL = "https://api.veldriklabs.com/whatsapp/dashboard/inbox"
BUSINESS_NAME = "Aura Beauty"


def owner_has_open_window():
    if not OWNER_PHONE_NUMBER:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM whatsapp_messages
        WHERE phone_number = %s
          AND incoming_message IS NOT NULL
          AND created_at >= NOW() - INTERVAL 24 HOUR
        ORDER BY created_at DESC
        LIMIT 1
    """, (OWNER_PHONE_NUMBER,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None


def notify_human_request(customer_phone, customer_name=None, incoming_message=None):
    if not OWNER_PHONE_NUMBER:
        raise RuntimeError("OWNER_PHONE_NUMBER no está configurado")

    customer_label = customer_name or "Cliente sin nombre"
    message_text = incoming_message or "Solicitó atención humana"

    if owner_has_open_window():
        alert = (
            "🚨 Atención humana requerida\n\n"
            f"Cliente: {customer_label}\n"
            f"Tel: {customer_phone}\n"
            f"Mensaje: {message_text}\n\n"
            f"Ver inbox:\n{DASHBOARD_INBOX_URL}"
        )

        print("OWNER NOTIFICATION MODE: normal message")

        return send_whatsapp_message(
            OWNER_PHONE_NUMBER,
            alert,
            os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            os.getenv("WHATSAPP_TOKEN"),
        )

    print("OWNER NOTIFICATION MODE: template")

    return send_human_support_template_message(
        OWNER_PHONE_NUMBER,
        BUSINESS_NAME,
        customer_label,
        message_text,
        os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        os.getenv("WHATSAPP_TOKEN"),
    )
