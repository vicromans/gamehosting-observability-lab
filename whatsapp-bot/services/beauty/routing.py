from services.conversation.state import conversation_state
from services.conversation.human import is_human_required


BOOKING_KEYWORDS = (
    "cita",
    "agendar",
    "agenda",
    "reservar",
    "reservación",
    "reservacion",
    "horario",
    "disponible",
    "disponibilidad",
)

HUMAN_KEYWORDS = (
    "humano",
    "persona",
    "asesora",
    "asesor",
    "hablar con alguien",
    "necesito hablar",
    "quiero hablar",
)

CONTROL_KEYWORDS = (
    "cancelar",
    "cancela",
    "ya no quiero",
    "mejor no",
    "olvídalo",
    "olvidalo",
    "gracias",
    "muchas gracias",
    "adiós",
    "adios",
    "hasta luego",
)

LOCATION_KEYWORDS = (
    "dirección",
    "direccion",
    "ubicación",
    "ubicacion",
    "domicilio",
    "dónde es",
    "donde es",
    "dónde queda",
    "donde queda",
)

MEDIA_KEYWORDS = (
    "foto",
    "fotos",
    "imagen",
    "imágenes",
    "imagenes",
    "muéstrame",
    "muestrame",
    "catálogo",
    "catalogo",
    "promoción",
    "promocion",
)

GREETING_ONLY = (
    "hola",
    "buenas",
    "buenos días",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "qué tal",
    "que tal",
    "hi",
)


def should_use_beauty_ai(message, phone_number):
    """
    Decide whether a Beauty text message should use BeautyAIService.

    Existing transactional/conversation flows always have priority.
    """
    text = (message or "").lower().strip()

    if not text:
        return False

    # Never interrupt an active legacy conversation flow.
    state = conversation_state.get(phone_number, {})

    if state.get("step"):
        return False

    # Preserve human handoff.
    if is_human_required(phone_number):
        return False

    # Booking remains deterministic in the legacy flow.
    if any(keyword in text for keyword in BOOKING_KEYWORDS):
        return False

    # Preserve operational/control messages.
    if any(keyword in text for keyword in HUMAN_KEYWORDS):
        return False

    if any(keyword in text for keyword in CONTROL_KEYWORDS):
        return False

    # Address handling currently has special privacy logic.
    if any(keyword in text for keyword in LOCATION_KEYWORDS):
        return False

    # Preserve catalog/media sending behavior.
    if any(keyword in text for keyword in MEDIA_KEYWORDS):
        return False

    # Cheap/simple greetings can remain deterministic.
    if text in GREETING_ONLY:
        return False

    # Everything else is informational/conversational AI territory.
    return True
