from services.conversation.state import conversation_state
from services.conversation.phrases import is_affirmative, is_negative, is_closing

from services.appointment_service import (
    save_appointment,
    is_time_slot_available,
    get_available_times,
    format_available_times_message,
)

from services.conversation_service import (
    parse_time_from_message,
    parse_date_from_message,
    clean_customer_name,
    format_date_for_user,
    try_handle_booking_message,
)


def handle_booking_flow(message, phone_number, state):
    text = message.lower().strip()

    booking_reply = try_handle_booking_message(
        message,
        phone_number,
        state,
        conversation_state
    )
    if booking_reply:
        return booking_reply



    if state.get("step") == "appointment_created":
        if is_closing(text) or is_affirmative(text):
            conversation_state[phone_number] = {}
            return "Perfecto 😊 Te esperamos el día de tu cita. Recuerda enviar tu comprobante de anticipo para confirmar tu lugar. ¡Gracias por elegir Aura Beauty! 💖"

        conversation_state[phone_number] = {}
        return None

    if state.get("step") == "confirm_booking":
        service = state.get("service", "servicio")

        if is_affirmative(text):
            conversation_state[phone_number] = {
                "step": "waiting_date",
                "service": service
            }
            return f"Perfecto 😊 ¿Qué día te gustaría agendar tu cita de {service}?"

        if is_negative(text):
            conversation_state[phone_number] = {}
            return "Con gusto 😊 Si después deseas agendar, aquí estaré para ayudarte."

        return "¿Te gustaría agendar una cita? Puedes responder sí o no 😊"

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

        appointment_date_text = format_date_for_user(appointment_date)
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
                    "date_text": appointment_date_text,
                    "appointment_date": str(appointment_date)
                }
                return f"Ese horario ya está ocupado 😔 Tengo disponible {available_text}. ¿Cuál prefieres?"

            conversation_state[phone_number] = {
                "step": "waiting_name",
                "service": service,
                "date_text": appointment_date_text,
                "appointment_date": str(appointment_date),
                "appointment_time": selected_time
            }

            return "Perfecto 😊 Ese horario está disponible. ¿A nombre de quién agendo la cita?"

        conversation_state[phone_number] = {
            "step": "waiting_time",
            "service": service,
            "date_text": appointment_date_text,
            "appointment_date": str(appointment_date)
        }

        if len(available_times) == 1:
            return f"Perfecto 😊 Solo tengo disponible {available_text}. ¿Te parece bien?"

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

        conversation_state[phone_number] = {
            "step": "appointment_created",
            "service": service
        }

        return f"Listo {customer_name} 😊 Tu cita de {service} quedó registrada para {date_text} a las {appointment_time[:5]}. Para confirmar se requiere anticipo de $150."

    return None
