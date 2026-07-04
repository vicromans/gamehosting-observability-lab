import os

from services.whatsapp_service import send_whatsapp_message


OWNER_PHONE_NUMBER = "5215587332824"
DASHBOARD_INBOX_URL = "https://api.veldriklabs.com/whatsapp/dashboard/inbox"


def notify_human_request(customer_phone, customer_name=None, incoming_message=None):
    customer_label = customer_name or "Cliente sin nombre"
    message_text = incoming_message or "Sin mensaje disponible"

    alert = (
        "🚨 Atención humana requerida\n\n"
        f"Cliente: {customer_label}\n"
        f"Tel: {customer_phone}\n"
        f"Mensaje: {message_text}\n\n"
        f"Ver inbox:\n{DASHBOARD_INBOX_URL}"
    )

    return send_whatsapp_message(
        OWNER_PHONE_NUMBER,
        alert,
        os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        os.getenv("WHATSAPP_TOKEN")
    )
