from flask import Blueprint, jsonify, send_from_directory, request, send_from_directory
from database.connection import get_db_connection

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
@public_bp.get("/whatsapp/")
def index():
    return jsonify({
        "service": "VeldrikLabs WhatsApp Bot",
        "status": "running"
    })


@public_bp.get("/whatsapp/static/<path:filename>")
def whatsapp_static(filename):
    return send_from_directory("static", filename)

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

@public_bp.get("/test")
@public_bp.get("/whatsapp/test")
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

@public_bp.get("/customers")
@public_bp.get("/whatsapp/customers")
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

