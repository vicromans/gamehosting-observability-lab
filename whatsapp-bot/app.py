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

app = Flask(__name__)
app.register_blueprint(dashboard_bp)

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

@app.get("/")
@app.get("/whatsapp/")
def index():
    return jsonify({
        "service": "VeldrikLabs WhatsApp Bot",
        "status": "running"
    })

def ensure_customer(phone_number):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO customers (phone_number)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE
                    last_contact = CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (phone_number,))

        connection.commit()
    finally:
        connection.close()

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

def save_message(phone_number, incoming_message, bot_reply_text, detected_intent):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO whatsapp_messages
                (phone_number, incoming_message, bot_reply, detected_intent)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                phone_number,
                incoming_message,
                bot_reply_text,
                detected_intent
            ))

        connection.commit()
    finally:
        connection.close()

def bot_reply(text):
    text = text.lower()

    if "anticipo" in text or "cita" in text or "agendar" in text:
        return "Para reservar cita se requiere un anticipo de $150 MXN. Por favor indícanos qué servicio deseas, día y horario preferido."

    if "hola" in text or "buenas" in text:
        return "Hola ✨ Bienvenida..."

    if "pestaña" in text:
        return "El servicio de pestañas tiene un precio regular de $500 MXN. Promoción actual: $350 MXN. Duración aproximada: 2 horas."

    if "uña" in text or "uñas" in text or "gel" in text or "gelish" in text or "semipermanente" in text:
        return "Para cotizar uñas, por favor envía una foto del diseño que te gustaría realizarte. El precio depende del diseño."

    if "alisado" in text or "cabello" in text:
        return "Para cotizar alisado progresivo, por favor envía una foto de tu cabello y comenta el largo aproximado. La duración aproximada es de 4 horas."

    if "horario" in text:
        return "Nuestro horario es de 9:00 AM a 12:00 PM y de 3:00 PM a 6:00 PM."

    if "pestaña" in text or "pestana" in text or "pestañas" in text or "pestanas" in text:
        return "El servicio de pestañas tiene un precio regular de $500 MXN. Promoción actual: $350 MXN. Duración aproximada: 2 horas."

    if "uña" in text or "unas" in text or "uñas" in text or "gelish" in text:
        return "Para cotizar uñas, por favor envía una foto del diseño que te gustaría realizarte. El precio depende del diseño."

    return "Gracias por escribirnos ✨ Para ayudarte mejor, dime si te interesa: uñas, pestañas o alisado progresivo."

@app.get("/test")
@app.get("/whatsapp/test")
def test_bot():
    msg = request.args.get("msg", "")
    phone = request.args.get("phone", "test-user")
    reply = bot_reply(msg)

    intent = "unknown"
    lower_msg = msg.lower()

    if "cita" in lower_msg or "agendar" in lower_msg or "anticipo" in lower_msg:
        intent = "appointment"
    elif "pestana" in lower_msg or "pestaña" in lower_msg:
        intent = "lashes"
    elif "una" in lower_msg or "uña" in lower_msg or "gel" in lower_msg or "gelish" in lower_msg or "semipermanente" in lower_msg:
        intent = "nails"
    elif "alisado" in lower_msg or "cabello" in lower_msg:
        intent = "hair"
    elif "horario" in lower_msg:
        intent = "schedule"
    elif "precio" in lower_msg or "costo" in lower_msg or "cuanto" in lower_msg or "cuánto" in lower_msg or "$" in lower_msg:
        intent = "pricing"
    elif "hola" in lower_msg or "buenas" in lower_msg:
        intent = "greeting"
        intent = "greeting"

    ensure_customer(phone)
    save_message(phone, msg, reply, intent)

    return jsonify({
        "incoming_message": msg,
        "bot_reply": reply,
        "detected_intent": intent,
        "saved": True
    })

@app.get("/customers")
@app.get("/whatsapp/customers")
def list_customers():
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    phone_number,
                    customer_name,
                    allergy_notes,
                    special_notes,
                    accepted_policies,
                    first_contact,
                    last_contact
                FROM customers
                ORDER BY last_contact DESC
                LIMIT 50
            """)
            customers = cursor.fetchall()

        return jsonify({
            "customers": customers,
            "count": len(customers)
        })

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

@app.get("/whatsapp/static/<path:filename>")
def whatsapp_static(filename):
    return send_from_directory("static", filename)

@app.get("/dashboard")
@app.get("/whatsapp/dashboard")
def dashboard():
    local_today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM businesses WHERE id = 1")
            business = cursor.fetchone()

            cursor.execute("""
                SELECT id, phone_number, customer_name, allergy_notes, accepted_policies, human_required, last_contact
                FROM customers
                WHERE business_id = 1
                ORDER BY human_required DESC, last_contact DESC
                LIMIT 10
            """)
            customers = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    phone_number,
                    customer_name,
                    last_contact
                FROM customers
                WHERE business_id = 1
                  AND human_required = 1
                ORDER BY last_contact DESC
            """)
            human_queue = cursor.fetchall()

            cursor.execute("""
                SELECT id, service_name, price, duration_minutes, requires_deposit, deposit_amount, warranty_days
                FROM services
                WHERE business_id = 1 AND active = 1
                ORDER BY id ASC
            """)
            services = cursor.fetchall()

            cursor.execute("""
                SELECT id, phone_number, incoming_message, detected_intent, created_at
                FROM whatsapp_messages
                WHERE business_id = 1
                ORDER BY created_at DESC
                LIMIT 10
            """)
            messages = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    customer_name,
                    customer_phone,
                    service_name,
                    appointment_date,
                    appointment_time,
                    status,
                    deposit_required,
                    deposit_paid,
                    created_at
                FROM appointments
                WHERE business_id = 1
                  AND appointment_date >= %s
                ORDER BY appointment_date ASC, appointment_time ASC
                LIMIT 20
            """, (local_today,))
            appointments = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    customer_name,
                    customer_phone,
                    service_name,
                    appointment_date,
                    appointment_time,
                    status,
                    deposit_required,
                    deposit_paid
                FROM appointments
                WHERE business_id = 1
                  AND appointment_date = %s
                ORDER BY appointment_time ASC
            """, (local_today,))
            today_appointments = cursor.fetchall()

        return render_template(
            "dashboard.html",
            business=business,
            customers=customers,
            human_queue=human_queue,
            services=services,
            messages=messages,
            appointments=appointments,
            today_appointments=today_appointments,
            local_today=local_today,
            active_page="dashboard"
        )


    finally:
        connection.close()

@app.get("/whatsapp/dashboard/clients")
def dashboard_clients():
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM businesses WHERE id = 1")
            business = cursor.fetchone()

            cursor.execute("""
                SELECT
                    id,
                    phone_number,
                    customer_name,
                    allergy_notes,
                    accepted_policies,
                    human_required,
                    last_contact
                FROM customers
                WHERE business_id = 1
                ORDER BY last_contact DESC
            """)
            customers = cursor.fetchall()

        return render_template(
            "clients.html",
            business=business,
            customers=customers,
            active_page="clients"
        )

    finally:
        connection.close()

@app.route("/dashboard/appointments/<int:appointment_id>/<action>", methods=["POST"])
@app.route("/whatsapp/dashboard/appointments/<int:appointment_id>/<action>", methods=["POST"])
def update_appointment_status(appointment_id, action):
    valid_actions = {
        "confirm": "confirmed",
        "cancel": "cancelled",
        "complete": "completed"
    }

    if action not in valid_actions:
        return "Acción inválida", 400

    new_status = valid_actions[action]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = %s
        WHERE id = %s AND business_id = 1
    """, (new_status, appointment_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/whatsapp/dashboard")

@app.route("/whatsapp/dashboard/inbox")
def dashboard_inbox():
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.customer_name,
                c.phone_number,
                c.human_required,
                (
                    SELECT incoming_message
                    FROM whatsapp_messages wm
                    WHERE wm.phone_number = c.phone_number
                    ORDER BY wm.created_at DESC
                    LIMIT 1
                ) AS last_message,
                (
                    SELECT created_at
                    FROM whatsapp_messages wm
                    WHERE wm.phone_number = c.phone_number
                    ORDER BY wm.created_at DESC
                    LIMIT 1
                ) AS last_message_at
            FROM customers c
            WHERE c.human_required = 1
            ORDER BY last_message_at DESC
        """)

        customers = cursor.fetchall()

        cursor.execute("SELECT * FROM businesses WHERE id = 1")
        business = cursor.fetchone()

        return render_template(
            "inbox.html",
            business=business,
            customers=customers,
            active_page="inbox"
        )

    finally:
        conn.close()

@app.route(
    "/whatsapp/dashboard/customers/<int:customer_id>/resolved",
    methods=["POST"]
)
def resolve_customer(customer_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE customers
        SET human_required = 0
        WHERE id = %s
    """, (customer_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/whatsapp/dashboard")

@app.route("/whatsapp/dashboard/customer/<int:customer_id>", methods=["GET", "POST"])
def customer_conversation(customer_id):

    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        if request.method == "POST":
            manual_reply = request.form.get("reply", "").strip()

            cursor.execute("""
                SELECT phone_number
                FROM customers
                WHERE id = %s
                LIMIT 1
            """, (customer_id,))

            customer_phone_row = cursor.fetchone()

            if manual_reply and customer_phone_row:
                phone_number = customer_phone_row["phone_number"]

                cursor.execute("""
                    INSERT INTO whatsapp_messages
                        (business_id, phone_number, incoming_message, bot_reply, detected_intent)
                    VALUES
                        (1, %s, NULL, %s, 'human_reply')
                """, (phone_number, manual_reply))

                send_whatsapp_message(
                    phone_number,
                    manual_reply,
                    WHATSAPP_PHONE_NUMBER_ID,
                    WHATSAPP_TOKEN
                )

                conn.commit()

            return redirect(f"/whatsapp/dashboard/customer/{customer_id}#bottom")

        cursor.execute("""
            SELECT
                id,
                customer_name,
                phone_number
            FROM customers
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        cursor.execute("""
            SELECT
                incoming_message, bot_reply,
                detected_intent,
                created_at
            FROM whatsapp_messages
            WHERE business_id = 1
              AND phone_number = %s
            ORDER BY created_at ASC
        """, (customer["phone_number"],))

        messages = cursor.fetchall()

        cursor.execute("SELECT * FROM businesses WHERE id = 1")
        business = cursor.fetchone()

        return render_template(
            "customer_conversation.html",
            business=business,
            customer=customer,
            messages=messages,
            active_page="clients"
        )

    finally:
        conn.close()

@app.route("/whatsapp/dashboard/customer/<int:customer_id>/send-template", methods=["POST"])
def send_customer_template(customer_id):
    template_name = request.form.get("template_name", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    topic = request.form.get("topic", "").strip()

    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT phone_number
            FROM customers
            WHERE id = %s
            LIMIT 1
        """, (customer_id,))

        customer = cursor.fetchone()

        if not customer:
            return redirect("/whatsapp/dashboard/clients")

        phone_number = customer["phone_number"]

        response = send_whatsapp_template_message(
            phone_number,
            template_name,
            customer_name,
            topic,
            WHATSAPP_PHONE_NUMBER_ID,
            WHATSAPP_TOKEN
        )

        if response.status_code in (200, 201):
            message_log = f"[Plantilla enviada] {template_name} para {customer_name}: {topic}"
            intent = "template_sent"
        else:
            friendly_error = translate_meta_error(response.text)

            message_log = (
                f"⚠️ {friendly_error['title']}\n"
                f"{friendly_error['message']}\n\n"
                f"Detalles técnicos: {friendly_error['technical']}"
            )

            intent = "template_error"

        cursor.execute("""
            INSERT INTO whatsapp_messages
                (business_id, phone_number, incoming_message, bot_reply, detected_intent)
            VALUES
                (1, %s, NULL, %s, %s)
        """, (
            phone_number,
            message_log,
            intent
        ))

        conn.commit()

        return redirect(f"/whatsapp/dashboard/customer/{customer_id}#bottom")

    finally:
        conn.close()

@app.route("/whatsapp/dashboard/customer/<int:customer_id>/messages")
def customer_messages_partial(customer_id):
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                phone_number
            FROM customers
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        if not customer:
            return ""

        cursor.execute("""
            SELECT
                incoming_message,
                bot_reply,
                detected_intent,
                created_at
            FROM whatsapp_messages
            WHERE business_id = 1
              AND phone_number = %s
            ORDER BY created_at ASC
        """, (customer["phone_number"],))

        messages = cursor.fetchall()

        html = ""

        for m in messages:
            created_at = m["created_at"]
            incoming = m["incoming_message"]
            bot_reply = m["bot_reply"]
            intent = m["detected_intent"]

            if incoming:
                html += f"""
                <div class="message customer">
                    <strong>{created_at}</strong><br>
                    <strong>Cliente:</strong> {incoming}<br>
                </div>
                """

            if bot_reply:
                label = "Bot"

                if intent == "human_reply":
                    label = "Asesora"

                html += f"""
                <div class="message bot">
                    <strong>{created_at}</strong><br>
                    <strong>{label}:</strong> {bot_reply}
                </div>
                """

        return html

    finally:
        conn.close()



@app.get("/whatsapp/dashboard/agenda")
def dashboard_agenda():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE business_id = %s
        ORDER BY appointment_date ASC, appointment_time ASC
        LIMIT 100
    """, (1,))
    appointments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="agenda",
        page_title="Agenda",
        page_description="Vista general de citas registradas.",
        items=appointments
    )


@app.get("/whatsapp/dashboard/services")
def dashboard_services():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM services
        WHERE business_id = %s
        ORDER BY service_name ASC
    """, (1,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="services",
        page_title="Servicios",
        page_description="Servicios configurados para Aura Beauty.",
        items=items
    )


@app.get("/whatsapp/dashboard/reports")
def dashboard_reports():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="reports",
        page_title="Reportes",
        page_description="Próximamente: clientes nuevos, servicios más vendidos e ingresos.",
        items=[]
    )


@app.get("/whatsapp/dashboard/settings")
def dashboard_settings():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="settings",
        page_title="Configuración",
        page_description="Próximamente: horarios, mensajes, anticipos y datos del negocio.",
        items=[]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
