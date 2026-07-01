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

from meta_errors import translate_meta_error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import requests
import re

from database.connection import get_db_connection
from routes.dashboard_routes import dashboard_bp
from routes.public_routes import public_bp

app = Flask(__name__)
app.register_blueprint(dashboard_bp)
app.register_blueprint(public_bp)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "veldriklabs_verify_2026")

conversation_state = {}

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

def build_reply(message, phone_number):
    text = message.lower().strip()
    state = conversation_state.get(phone_number, {})

    bot_keywords = [
        "sigue tu",
        "sigue tú",
        "atiende tu",
        "atiende tú",
        "quiero seguir con el bot",
        "que me atienda el bot",
        "bot",
        "automatico",
        "automático",
        "quiero agendar",
        "agendar cita",
        "cita"
    ]

    if state.get("step") == "human_required" and any(keyword in text for keyword in bot_keywords):
        conversation_state[phone_number] = {}
        clear_human_required(phone_number)
        return "Claro 😊 Seguimos con el bot. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"

    human_keywords = [
        "humano",
        "persona",
        "asesora",
        "asesor",
        "alguien",
        "hablar con alguien",
        "necesito hablar",
        "quiero hablar",
        "no entiendo",
        "no entendi",
        "ayuda",
        "soporte"
    ]

    if any(keyword in text for keyword in human_keywords):
        mark_human_required(phone_number)
        return "Claro 😊 Una asesora de Aura Beauty revisará tu mensaje. Mientras tanto, también puedo ayudarte con citas, precios, pestañas, uñas o alisado."

    cancel_keywords = [
        "no lo quiero",
        "ya no quiero",
        "mejor no",
        "cancelar",
        "cancela",
        "olvidalo",
        "olvídalo",
        "dejalo",
        "déjalo"
    ]

    if any(keyword in text for keyword in cancel_keywords):
        conversation_state[phone_number] = {}
        return "Claro 😊 Cancelé esta solicitud. Si después quieres agendar otra cita, aquí estoy."

    if any(word in text for word in ["gracias", "muchas gracias", "thank you", "thanks", "mil gracias"]):
        conversation_state[phone_number] = {}
        return "¡Con gusto! 😊 Gracias por contactar a Aura Beauty. Si necesitas algo más, aquí estoy."

    if any(word in text for word in ["bye", "adios", "adiós", "hasta luego", "nos vemos", "chao", "ciao"]):
        return "¡Hasta luego! 😊 Gracias por contactar a Aura Beauty. Te esperamos pronto."

    booking_reply = try_handle_booking_message(
        message,
        phone_number,
        state,
        conversation_state
    )
    if booking_reply:
        return booking_reply

    if state.get("step") == "waiting_service":
        if any(word in text for word in ["pestaña", "pestañas", "lash", "lashes"]):
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": "pestañas"
            }
            return "Perfecto ✨ ¿Qué día te gustaría agendar tu cita de pestañas?"

        if any(word in text for word in ["uña", "uñas", "nail", "nails", "gel", "gelish", "semipermanente"]):
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": "uñas"
            }
            return "Perfecto 💅 ¿Qué día te gustaría agendar tu cita de uñas?"

        if any(word in text for word in ["alisado", "keratina", "cabello", "pelo"]):
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": "alisado"
            }
            return "Perfecto ✨ ¿Qué día te gustaría agendar tu cita de alisado?"

        return "¿Qué servicio deseas agendar: pestañas, uñas o alisado?"

    if state.get("step") == "waiting_date":
        appointment_date = parse_date_from_message(message)
        selected_time = parse_time_from_message(message)
        service = state.get("service")

        if not appointment_date:
            return "¿Qué día te gustaría? Puedes decir: hoy, mañana, pasado mañana, lunes, martes, miércoles, jueves, viernes, sábado o domingo 😊"

        available_times = get_available_times(str(appointment_date), service)
        available_text = format_available_times_message(available_times)

        if not available_text:
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": service,
                "retry_reason": "no_availability"
            }
            return "Lo siento 😔 Ya no tengo horarios disponibles para ese día. ¿Qué otro día te gustaría intentar?"

        if selected_time:
            if not is_time_slot_available(str(appointment_date), selected_time, service):
                conversation_state[phone_number] = {
                    "step": "waiting_time",
                    "service": service,
                    "date_text": format_date_for_user(appointment_date_text),
                    "appointment_date": str(appointment_date)
                }
                return f"Ese horario ya está ocupado 😔 Tengo disponible {available_text}. ¿Cuál prefieres?"

            conversation_state[phone_number] = {
                "step": "waiting_name",
                "service": service,
                "date_text": format_date_for_user(appointment_date_text),
                "appointment_date": str(appointment_date),
                "appointment_time": selected_time
            }

            return "Perfecto 😊 Ese horario está disponible. ¿A nombre de quién agendo la cita?"

        conversation_state[phone_number] = {
            "step": "waiting_time",
            "service": service,
            "date_text": format_date_for_user(appointment_date_text),
            "appointment_date": str(appointment_date)
        }

        if len(available_times) == 1:
            return f"Perfecto 😊 Solo tengo disponible {available_text}. ¿Te parece bien?"
        else:
            return f"Perfecto 😊 Tengo disponible {available_text}. ¿Qué horario prefieres?"

    if state.get("step") == "waiting_time":
        selected_time = parse_time_from_message(message)

        if not selected_time:
            appointment_date = state.get("appointment_date")
            available_times = get_available_times(appointment_date, state.get("service"))
            available_text = format_available_times_message(available_times)

            if available_text:
                return f"Por ahora tengo disponible {available_text}. Puedes decir: a las 10, medio día o 3 pm 😊"

            conversation_state[phone_number] = {}
            return "Lo siento 😔 Ese día ya no tiene horarios disponibles. ¿Quieres intentar con otro día?"

        service = state.get("service", "servicio")
        date_text = state.get("date_text", "pendiente")

        appointment_date = state.get("appointment_date")

        if not is_time_slot_available(appointment_date, selected_time, service):

            available_times = get_available_times(appointment_date, state.get("service"))
            available_text = format_available_times_message(available_times)

            if not available_text:
                conversation_state[phone_number] = {}
                return "Lo siento 😔 Ese día ya no tiene horarios disponibles. ¿Quieres intentar con otro día?"

            if len(available_times) == 1:
                return f"Ese horario ya está ocupado 😔 Solo me queda disponible {available_text}. ¿Te funciona ese horario?"
            else:
                return f"Ese horario ya está ocupado 😔 Tengo disponible {available_text}. ¿Cuál prefieres?"

        conversation_state[phone_number] = {
            "step": "waiting_name",
            "service": service,
            "date_text": date_text,
            "appointment_date": appointment_date,
            "appointment_time": selected_time
        }

        return "Perfecto 😊 ¿A nombre de quién agendo la cita?"

    if state.get("step") == "waiting_name":
        customer_name = clean_customer_name(message)

        if len(customer_name) < 2:
            return "¿Me puedes decir el nombre para agendar la cita, por favor? 😊"

        service = state.get("service")
        date_text = state.get("date_text")
        appointment_date = state.get("appointment_date")
        appointment_time = state.get("appointment_time")

        save_appointment(
            phone_number,
            customer_name,
            service,
            appointment_date,
            appointment_time
        )

        conversation_state[phone_number] = {}

        return f"Listo {customer_name} 😊 Tu cita de {service} quedó registrada para {date_text} a las {appointment_time[:5]}. Para confirmar se requiere anticipo de $150."

    if state.get("waiting_for") == "hair_length":
        if any(word in text for word in ["corto", "corta"]):
            conversation_state[phone_number] = {}
            return "Perfecto 😊 Para cabello corto, el alisado tarda aprox. 4 horas. ¿Quieres agendar una cita?"
        if any(word in text for word in ["medio", "mediano", "media"]):
            conversation_state[phone_number] = {}
            return "Perfecto 😊 Para cabello medio, el alisado requiere valoración de largo y volumen. ¿Quieres agendar una cita?"
        if any(word in text for word in ["largo", "larga"]):
            conversation_state[phone_number] = {}
            return "Perfecto 😊 Para cabello largo, el precio depende del volumen. ¿Quieres agendar una cita?"

        return "Para ayudarte con el alisado, dime si tu cabello es corto, medio o largo 😊"

    if any(word in text for word in ["alisado", "cabello", "pelo", "keratina"]):
        conversation_state[phone_number] = {"waiting_for": "hair_length"}
        return "El alisado progresivo depende del largo del cabello y dura aproximadamente 4 horas. ¿Tu cabello es corto, medio o largo?"


    if any(word in text for word in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "buen dia", "que onda", "qué onda", "que tal", "qué tal",
    "hola que tal", "hola qué tal", "hey", "hi", "kiubo", "quiubo", "que hay", "que rollo"]):
        return "¡Hola! 😊 Bienvenida a Aura Beauty. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"

    if any(word in text for word in ["cita", "agendar", "agenda", "horario", "disponible"]):
        conversation_state[phone_number] = {"step": "waiting_service"}
        return "Claro 😊 Te ayudo a agendar. ¿Qué servicio necesitas: pestañas, uñas o alisado?"

    if any(word in text for word in ["pestaña", "pestañas", "lash", "lashes"]):
        return "Para pestañas tenemos promoción en $350 ✨ Para agendar se requiere anticipo de $150. ¿Quieres agendar una cita?"

    if any(word in text for word in ["uña", "uñas", "nail", "nails", "gel", "gelish", "semipermanente"]):
        return "Para uñas tenemos opciones desde $125 en gel semipermanente. Acrílico desde $250 y esculturales desde $300 según largo. Para agendar se requiere anticipo de $150 💅 ¿Qué servicio buscas?"

    if any(word in text for word in ["alisado", "cabello", "pelo", "keratina"]):
        return "El alisado progresivo depende del largo del cabello y dura aproximadamente 4 horas. ¿Tu cabello es corto, medio o largo?"

    if any(word in text for word in ["precio", "costo", "cuanto", "cuánto", "$"]):
        return "Te comparto precios base: pestañas $500, uñas según diseño y alisado según largo del cabello. ¿Sobre cuál servicio quieres más información?"

    if any(phrase in text for phrase in [
        "hablar con alguien",
        "hablar con una persona",
        "quiero una persona",
        "quiero hablar con alguien",
        "asesora",
        "humano",
        "persona real",
        "me puedes comunicar",
        "comunicarme con alguien",
        "no entiendo",
        "no entendi",
        "no entendí",
        "necesito ayuda"
    ]):
        conversation_state[phone_number] = {
            "step": "human_required"
        }

        mark_human_required(phone_number)

        return "Claro 😊 Voy a canalizarte con una asesora de Aura Beauty para que te ayude personalmente. En breve te responderán."

    return "Perdón, no entendí bien 🙏 Puedo ayudarte con citas, precios, pestañas, uñas o alisado."

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

def mark_human_required(phone_number):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE customers
                SET human_required = TRUE,
                    last_contact = CURRENT_TIMESTAMP
                WHERE phone_number = %s
            """, (phone_number,))

        connection.commit()
    finally:
        connection.close()

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
