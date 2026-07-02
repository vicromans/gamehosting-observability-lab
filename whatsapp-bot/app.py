from flask import (
    Flask,
    request,
    jsonify,
    redirect,
    render_template,
    send_from_directory
)
from services.whatsapp_service import (
    send_whatsapp_message,
    send_whatsapp_template_message,
)

from services.appointment_service import (
    get_service_duration_minutes,
    save_appointment,
    time_to_minutes,
    ranges_overlap,
    is_time_slot_available,
    format_time_for_user,
    is_slot_blocked,
    is_day_blocked,
    get_available_times,
    format_available_times_message,
)

from services.conversation_service import (
    parse_time_from_message,
    parse_date_from_message,
    clean_customer_name,
    format_date_for_user,
    extract_service_from_message,
    is_affirmative_message,
    extract_booking_information,
    is_booking_intent,
    build_available_times_reply,
    try_handle_booking_message,
)

from services.conversation.human import (
    mark_human_required,
    clear_human_required,
)

from meta_errors import translate_meta_error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import requests
import re

from database.connection import get_db_connection
from routes.dashboard_routes import dashboard_bp
from routes.public_routes import public_bp
from services.conversation.state import conversation_state
from services.conversation.booking import handle_booking_flow
from services.conversation.hair import handle_hair_flow
from services.conversation.engine import build_reply

app = Flask(__name__)
app.register_blueprint(dashboard_bp)
app.register_blueprint(public_bp)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "veldriklabs_verify_2026")

VERIFY_TOKEN = "veldriklabs_whatsapp_verify"

@app.get("/webhook")
@app.get("/whatsapp/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("WEBHOOK VERIFIED", flush=True)
        return challenge, 200

    return "Verification failed", 403

@app.post("/webhook")
@app.post("/whatsapp/webhook")
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
        message_type = message.get("type")
        whatsapp_message_id = message.get("id")

        customer_waiting_human = False

        check_conn = get_db_connection()
        try:
            with check_conn.cursor() as check_cursor:
                check_cursor.execute("""
                    SELECT human_required
                    FROM customers
                    WHERE phone_number = %s
                    LIMIT 1
                """, (phone_number,))
                row = check_cursor.fetchone()

                if row and row["human_required"]:
                    customer_waiting_human = True
        finally:
            check_conn.close()

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

def appointment_actions(a):
    appointment_id = a["id"]
    status = a["status"]

    if status == "pending":
        return f"""
            <form method="POST" action="/whatsapp/dashboard/appointments/{appointment_id}/confirm" style="display:inline;">
                <button type="submit">Confirmar</button>
            </form>
            <form method="POST" action="/whatsapp/dashboard/appointments/{appointment_id}/cancel" style="display:inline;">
                <button type="submit">Cancelar</button>
            </form>
        """

    if status == "confirmed":
        return f"""
            <form method="POST" action="/whatsapp/dashboard/appointments/{appointment_id}/complete" style="display:inline;">
                <button type="submit">Completada</button>
            </form>
            <form method="POST" action="/whatsapp/dashboard/appointments/{appointment_id}/cancel" style="display:inline;">
                <button type="submit">Cancelar</button>
            </form>
        """

    if status == "completed":
        return "✅ Finalizada"

    if status == "cancelled":
        return "❌ Cancelada"

    return status

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
