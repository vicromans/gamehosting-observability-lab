import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def normalize_message_text(message):
    text = message.lower().strip()

    replacements = {
        "ma;ana": "mañana",
        "man;ana": "mañana",
        "manana": "mañana",
        "mediodia": "mediodía",
        "medio dia": "mediodía",
        "pestanas": "pestañas",
        "unas": "uñas",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def parse_time_from_message(message):
    text = normalize_message_text(message)

    if any(phrase in text for phrase in ["10", "diez"]):
        return "10:00:00"

    if any(phrase in text for phrase in ["12", "doce", "medio dia", "mediodia", "medio día", "mediodía"]):
        return "12:00:00"

    if any(phrase in text for phrase in ["15", "3", "tres", "3 pm", "3pm"]):
        return "15:00:00"

    return None


def parse_date_from_message(message):
    text = normalize_message_text(message)
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()

    months = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }

    numeric_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if numeric_match:
        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year_text = numeric_match.group(3)

        if year_text:
            year = int(year_text)
            if year < 100:
                year += 2000
        else:
            year = today.year

        try:
            candidate = datetime(year, month, day).date()
            if not year_text and candidate < today:
                candidate = datetime(year + 1, month, day).date()
            return candidate
        except ValueError:
            pass

    month_names = "|".join(months.keys())
    text_match = re.search(rf"\b(?:dia|día)?\s*(\d{{1,2}})\s*(?:de\s*)?({month_names})(?:\s*(?:de\s*)?(\d{{4}}))?\b", text)
    if text_match:
        day = int(text_match.group(1))
        month = months[text_match.group(2)]
        year = int(text_match.group(3)) if text_match.group(3) else today.year

        try:
            candidate = datetime(year, month, day).date()
            if not text_match.group(3) and candidate < today:
                candidate = datetime(year + 1, month, day).date()
            return candidate
        except ValueError:
            pass

    if "hoy" in text:
        return today

    if "pasado mañana" in text or "pasado manana" in text:
        return today + timedelta(days=2)

    if "mañana" in text or "manana" in text:
        return today + timedelta(days=1)

    weekdays = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "miércoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "sábado": 5,
        "domingo": 6,
    }

    for day_name, day_number in weekdays.items():
        if day_name in text:
            days_ahead = day_number - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    return None


def clean_customer_name(message):
    text = message.strip()

    prefixes = [
        "a mi nombre",
        "mi nombre es",
        "soy",
        "me llamo",
        "a nombre de",
        "nombre",
    ]

    lower_text = text.lower()

    for prefix in prefixes:
        if lower_text.startswith(prefix):
            return text[len(prefix):].strip(" ,.-:")

    return text


def format_date_for_user(date_text):
    try:
        date_obj = datetime.strptime(str(date_text), "%Y-%m-%d").date()
    except ValueError:
        return str(date_text)

    weekdays = [
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
    ]

    return f"{weekdays[date_obj.weekday()]} {date_obj.day}/{date_obj.month}"


def extract_service_from_message(message):
    text = normalize_message_text(message)

    if "pestaña" in text or "pestana" in text:
        return "pestañas"

    if "uña" in text or "una" in text:
        return "uñas"

    if "alisado" in text or "keratina" in text:
        return "alisado"

    return None


def is_affirmative_message(message):
    text = normalize_message_text(message)

    affirmative_words = [
        "si",
        "sí",
        "claro",
        "ok",
        "vale",
        "va",
        "correcto",
        "adelante",
        "por favor",
        "bambi es un venado",
    ]

    return any(word in text for word in affirmative_words)


def extract_booking_information(message):
    return {
        "service": extract_service_from_message(message),
        "date": parse_date_from_message(message),
        "time": parse_time_from_message(message),
    }


def is_booking_intent(message):
    text = normalize_message_text(message)

    keywords = [
        "cita",
        "agendar",
        "agenda",
        "reservar",
        "reservación",
        "reservacion",
        "turno",
    ]

    return any(keyword in text for keyword in keywords)


def build_available_times_reply(
    available_times,
    conversation_state,
    phone_number=None,
    service=None,
    appointment_date_text=None
):
    from services.appointment_service import format_available_times_message

    available_text = format_available_times_message(available_times)

    if not available_text:
        return None

    if len(available_times) == 1:
        if phone_number and service and appointment_date_text:
            conversation_state[phone_number] = {
                "step": "waiting_time_confirmation",
                "service": service,
                "date_text": format_date_for_user(appointment_date_text),
                "appointment_date": appointment_date_text,
                "suggested_time": available_times[0]
            }
        return f"Solo tengo disponible {available_text}. ¿Te parece bien?"

    return f"Tengo disponible {available_text}. ¿Qué horario prefieres?"


def try_handle_booking_message(message, phone_number, state, conversation_state):
    from services.appointment_service import (
        get_available_times,
        is_time_slot_available,
        format_available_times_message,
    )

    booking = extract_booking_information(message)

    service = booking.get("service") or state.get("service")
    appointment_date = booking.get("date") or state.get("appointment_date")
    selected_time = booking.get("time")

    if not selected_time and state.get("step") == "waiting_time_confirmation" and is_affirmative_message(message):
        selected_time = state.get("suggested_time")

        if selected_time and service and appointment_date:
            appointment_date_text = str(appointment_date)
            conversation_state[phone_number] = {
                "step": "waiting_name",
                "service": service,
                "date_text": format_date_for_user(appointment_date_text),
                "appointment_date": appointment_date_text,
                "appointment_time": selected_time
            }
            return "Perfecto 😊 ¿A nombre de quién agendo la cita?"

    has_booking_data = booking.get("service") or booking.get("date") or booking.get("time")
    active_booking_flow = state.get("step") in ["waiting_service", "waiting_date", "waiting_time", "waiting_time_confirmation"]
    booking_intent = is_booking_intent(message)

    if not has_booking_data and not active_booking_flow and not booking_intent:
        return None

    if booking.get("service") and not booking.get("date") and not booking.get("time") and not active_booking_flow and not booking_intent:
        return None

    if not service:
        conversation_state[phone_number] = {"step": "waiting_service"}
        return "Claro 😊 Te ayudo a agendar. ¿Qué servicio necesitas: pestañas, uñas o alisado?"

    if not appointment_date:
        conversation_state[phone_number] = {
            "step": "waiting_date",
            "service": service
        }
        return f"Perfecto 😊 ¿Qué día te gustaría agendar tu cita de {service}?"

    appointment_date_text = str(appointment_date)

    if not selected_time:
        available_times = get_available_times(appointment_date_text, service)
        reply = build_available_times_reply(
            available_times,
            conversation_state,
            phone_number,
            service,
            appointment_date_text
        )

        if not reply:
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": service,
                "retry_reason": "no_availability"
            }
            return "Lo siento 😔 Ya no tengo horarios disponibles para ese día. ¿Qué otro día te gustaría intentar?"

        if len(available_times) == 1:
            return f"Perfecto 😊 {reply}"

        conversation_state[phone_number] = {
            "step": "waiting_time",
            "service": service,
            "date_text": format_date_for_user(appointment_date_text),
            "appointment_date": appointment_date_text
        }

        return f"Perfecto 😊 {reply}"

    if not is_time_slot_available(appointment_date_text, selected_time, service):
        available_times = get_available_times(appointment_date_text, service)
        available_text = format_available_times_message(available_times)

        conversation_state[phone_number] = {
            "step": "waiting_time",
            "service": service,
            "date_text": format_date_for_user(appointment_date_text),
            "appointment_date": appointment_date_text
        }

        if not available_text:
            return "Lo siento 😔 Ese día ya no tiene horarios disponibles. ¿Quieres intentar con otro día?"

        if len(available_times) == 1:
            conversation_state[phone_number] = {
                "step": "waiting_time_confirmation",
                "service": service,
                "date_text": format_date_for_user(appointment_date_text),
                "appointment_date": appointment_date_text,
                "suggested_time": available_times[0]
            }
            return f"Ese horario ya no está disponible 😔 Solo me queda {available_text}. ¿Te funciona ese horario?"

        return f"Ese horario ya no está disponible 😔 Tengo disponible {available_text}. ¿Cuál prefieres?"

    conversation_state[phone_number] = {
        "step": "waiting_name",
        "service": service,
        "date_text": format_date_for_user(appointment_date_text),
        "appointment_date": appointment_date_text,
        "appointment_time": selected_time
    }

    return "Perfecto 😊 Ese horario está disponible. ¿A nombre de quién agendo la cita?"
