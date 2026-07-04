from services.conversation.state import conversation_state
from services.conversation.human import (
    mark_human_required,
    clear_human_required,
)
from services.conversation.booking import handle_booking_flow
from services.conversation.hair import handle_hair_flow


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

    booking_reply = handle_booking_flow(message, phone_number, state)
    if booking_reply:
        return booking_reply

    hair_reply = handle_hair_flow(message, phone_number, state)
    if hair_reply:
        return hair_reply

    if any(word in text for word in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "buen dia", "que onda", "qué onda", "que tal", "qué tal",
    "hola que tal", "hola qué tal", "hey", "hi", "kiubo", "quiubo", "que hay", "que rollo"]):
        return "¡Hola! 😊 Bienvenida a Aura Beauty. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"

    if any(word in text for word in ["cita", "agendar", "agenda", "horario", "disponible"]):
        conversation_state[phone_number] = {"step": "waiting_service"}
        return "Claro 😊 Te ayudo a agendar. ¿Qué servicio necesitas: pestañas, uñas o alisado?"

    if any(word in text for word in ["pestaña", "pestañas", "lash", "lashes"]):
        conversation_state[phone_number] = {"step": "confirm_booking", "service": "pestañas"}
        return "Para pestañas tenemos promoción en $350 ✨ Para agendar se requiere anticipo de $150. ¿Quieres agendar una cita?"

    if any(word in text for word in ["uña", "uñas", "nail", "nails", "gel", "gelish", "semipermanente"]):
        conversation_state[phone_number] = {"step": "confirm_booking", "service": "uñas"}
        return "Para uñas tenemos opciones desde $125 en gel semipermanente. Acrílico desde $250 y esculturales desde $300 según largo. Para agendar se requiere anticipo de $150 💅 ¿Quieres agendar una cita?"

    if any(word in text for word in ["alisado", "cabello", "pelo", "keratina"]):
        return "El alisado progresivo depende del largo del cabello y dura aproximadamente 4 horas. ¿Tu cabello es corto, medio o largo?"

    if any(word in text for word in ["precio", "costo", "cuanto", "cuánto", "$"]):
        return "Te comparto precios base: pestañas $500, uñas según diseño y alisado según largo del cabello. ¿Sobre cuál servicio quieres más información?"

    return "Perdón, no entendí bien 🙏 Puedo ayudarte con citas, precios, pestañas, uñas o alisado."


def build_replies(message, phone_number):
    text = message.lower().strip()

    greeting_words = [
        "hola", "buenas", "buenos dias", "buenos días",
        "buenas tardes", "buenas noches", "buen dia",
        "que tal", "qué tal", "que onda", "qué onda", "hi"
    ]

    has_greeting = any(word in text for word in greeting_words)

    has_nails = any(word in text for word in [
        "uña", "uñas", "nail", "nails", "gel", "gelish",
        "semipermanente", "acrilico", "acrílico", "esculturales"
    ])

    has_lashes = any(word in text for word in [
        "pestaña", "pestañas", "lash", "lashes"
    ])

    has_hair = any(word in text for word in [
        "alisado", "cabello", "pelo", "keratina"
    ])

    has_booking = any(word in text for word in [
        "cita", "agendar", "agenda", "horario", "disponible"
    ])

    if has_greeting and (has_nails or has_lashes or has_hair or has_booking):
        replies = [
            "¡Hola! 😊 Bienvenida a Aura Beauty. Será un gusto atenderte."
        ]

        if has_nails:
            replies.append(
                "Claro 💅 Con gusto te doy información de uñas. "
                "Tenemos gel semipermanente, acrílico y esculturales. "
                "El precio depende del largo y diseño. Para agendar se requiere anticipo."
            )
            replies.append("¿Qué tipo de uñas te interesa: gel, acrílico o esculturales?")

        elif has_lashes:
            replies.append(
                "Claro ✨ Para pestañas tenemos promoción en $350. "
                "Para agendar se requiere anticipo de $150."
            )
            replies.append("¿Te gustaría agendar una cita para pestañas?")

        elif has_hair:
            replies.append(
                "Claro 😊 El alisado progresivo depende del largo del cabello "
                "y dura aproximadamente 4 horas."
            )
            replies.append("¿Tu cabello es corto, medio o largo?")

        elif has_booking:
            conversation_state[phone_number] = {"step": "waiting_service"}
            replies.append("Claro 😊 Te ayudo a agendar.")
            replies.append("¿Qué servicio necesitas: pestañas, uñas o alisado?")

        return replies

    return [build_reply(message, phone_number)]
