import os

from flask import Blueprint, jsonify, request

from database.connection import get_db_connection
from services.conversation.engine import build_reply
from services.conversation.human import mark_human_required
from services.whatsapp_service import send_whatsapp_message

whatsapp_bp = Blueprint("whatsapp", __name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "veldriklabs_verify_2026")


@whatsapp_bp.get("/webhook")
@whatsapp_bp.get("/whatsapp/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("WEBHOOK VERIFIED", flush=True)
        return challenge, 200

    return "Verification failed", 403


@whatsapp_bp.post("/webhook")
@whatsapp_bp.post("/whatsapp/webhook")
def receive_message():
    data = request.get_json()

    print("=" * 80, flush=True)
    print("INCOMING WHATSAPP WEBHOOK", flush=True)
    print(data, flush=True)
    print("=" * 80, flush=True)

    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        contacts = value.get("contacts", [])
        messages = value.get("messages", [])

        if not messages:
            return jsonify({"status": "no_message"}), 200

        contact = contacts[0] if contacts else {}
        message = messages[0]

        phone_number = message.get("from")
        customer_name = contact.get("profile", {}).get("name")
        incoming_message = message.get("text", {}).get("body", "")

        reply = build_reply(incoming_message, phone_number)

        if reply and "canalizar" in reply:
            mark_human_required(phone_number)

        intent = "unknown"
        lower_msg = incoming_message.lower()

        if "cita" in lower_msg or "agendar" in lower_msg or "anticipo" in lower_msg:
            intent = "appointment"
        elif "pestana" in lower_msg or "pestaña" in lower_msg or "pestañas" in lower_msg:
            intent = "lashes"
        elif "una" in lower_msg or "uña" in lower_msg or "uñas" in lower_msg or "gel" in lower_msg or "gelish" in lower_msg or "semipermanente" in lower_msg:
            intent = "nails"
        elif "alisado" in lower_msg or "cabello" in lower_msg:
            intent = "hair"
        elif "horario" in lower_msg:
            intent = "schedule"
        elif "precio" in lower_msg or "costo" in lower_msg or "cuanto" in lower_msg or "cuánto" in lower_msg or "$" in lower_msg:
            intent = "pricing"
        elif "hola" in lower_msg or "buenas" in lower_msg:
            intent = "greeting"

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO customers (business_id, phone_number, customer_name)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        customer_name = VALUES(customer_name),
                        last_contact = CURRENT_TIMESTAMP
                """, (1, phone_number, customer_name))

                cursor.execute("""
                    INSERT INTO whatsapp_messages
                    (business_id, phone_number, incoming_message, bot_reply, detected_intent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (1, phone_number, incoming_message, reply, intent))

            connection.commit()

        finally:
            connection.close()

        print(f"Saved WhatsApp message from {phone_number}: {incoming_message}", flush=True)

        if reply:
            send_whatsapp_message(
                phone_number,
                reply,
                WHATSAPP_PHONE_NUMBER_ID,
                WHATSAPP_TOKEN
            )

        return jsonify({
            "status": "saved",
            "phone_number": phone_number,
            "message": incoming_message,
            "intent": intent
        }), 200

    except Exception as e:
        print("ERROR processing webhook:", str(e), flush=True)
        return jsonify({"status": "error", "error": str(e)}), 200
