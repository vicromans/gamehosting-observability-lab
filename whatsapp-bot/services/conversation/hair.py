from services.conversation.state import conversation_state


def handle_hair_flow(message, phone_number, state):
    text = message.lower().strip()

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

    return None
