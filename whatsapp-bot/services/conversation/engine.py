from services.conversation.state import conversation_state
from services.conversation.human import (
    clear_human_required,
    handle_human_request,
    is_human_required,
)
from services.conversation.booking import handle_booking_flow
from services.catalog.catalog import send_catalog_item
from services.catalog.detector import detect_catalog_item
from services.conversation.hair import handle_hair_flow
from services.customer_service import get_customer_display_name, customer_has_future_appointment


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

    if (state.get("step") == "human_required" or is_human_required(phone_number)) and any(keyword in text for keyword in bot_keywords):
        conversation_state[phone_number] = {}
        clear_human_required(phone_number)
        return "Claro 😊 Seguimos con el bot. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"

    if is_human_required(phone_number):
        return None

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
        handle_human_request(phone_number, incoming_message=message)
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

    if any(word in text for word in ["direccion", "dirección", "ubicacion", "ubicación", "domicilio", "donde es", "dónde es", "donde estan", "dónde están", "donde queda", "dónde queda"]):
        if customer_has_future_appointment(phone_number):
            return "Claro 😊 Tu cita será en casa de Mercedes. La dirección es: Av. Sta. Lucía 104, Edificio Durango #68, Santa María Nonoalco, Álvaro Obregón, 01420 Ciudad de México, CDMX."
        return "Las citas se realizan en casa de Mercedes 😊 La dirección completa se comparte cuando la cita ya está registrada."

    if any(word in text for word in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "buen dia", "que onda", "qué onda", "que tal", "qué tal",
    "hola que tal", "hola qué tal", "hey", "hi", "kiubo", "quiubo", "que hay", "que rollo"]):
        display_name = get_customer_display_name(phone_number)
        if display_name:
            return f"Hola {display_name} 😊 Qué gusto volver a saludarte. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"
        return "¡Hola! 😊 Bienvenida a Aura Beauty. Puedo ayudarte con citas, precios, pestañas, uñas o alisado. ¿Qué necesitas?"

    if any(word in text for word in ["cita", "agendar", "agenda", "horario", "disponible"]):
        conversation_state[phone_number] = {"step": "waiting_service"}
        return "Claro 😊 Te ayudo a agendar. ¿Qué servicio necesitas: pestañas, uñas o alisado?"

    from services.catalog.catalog import get_catalog_item

    catalog_item = detect_catalog_item(text)
    if catalog_item:
        send_catalog_item(phone_number, catalog_item)
        conversation_state[phone_number] = {"step": "confirm_booking", "service": catalog_item}
        item = get_catalog_item(catalog_item)
        title = item.get("title", catalog_item)
        return f"¿Quieres agendar una cita para {title}?"

    if any(word in text for word in ["alisado", "cabello", "pelo", "keratina"]):
        return "El alisado progresivo depende del largo del cabello y dura aproximadamente 4 horas. ¿Tu cabello es corto, medio o largo?"

    if any(word in text for word in ["precio", "costo", "cuanto", "cuánto", "$"]):
        return "Te comparto precios base: pestañas precio regular $500, por promoción vigente $350; Gelish/Gel desde $120; uñas acrílicas desde $250; y alisado según largo del cabello. ¿Sobre cuál servicio quieres más información?"

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
        "semipermanente", "acrilico", "acrílico"
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
                "Tenemos Gelish/Gel desde $120 y uñas acrílicas desde $250. "
                "Los diseños elaborados pueden variar según decoración y detalle. Para agendar se requiere anticipo."
            )
            replies.append("¿Qué tipo de uñas te interesa: Gelish/Gel o acrílicas?")

        elif has_lashes:
            send_catalog_item(phone_number, "pestañas")
            replies.append("Claro ✨ Te comparto la promoción vigente de pestañas.")
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
