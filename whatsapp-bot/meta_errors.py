def translate_meta_error(response_text):
    """
    Convierte errores técnicos de Meta/WhatsApp en mensajes entendibles
    para el usuario final del Dashboard.
    """
    import json

    default_result = {
        "title": "No se pudo enviar el mensaje",
        "message": "Meta no aceptó el envío. Revisa la configuración de WhatsApp Business o intenta nuevamente más tarde.",
        "technical": response_text,
        "code": None
    }

    try:
        data = json.loads(response_text)
        error = data.get("error", {})
        code = error.get("code")
        details = error.get("error_data", {}).get("details") or error.get("message", response_text)
    except Exception:
        return default_result

    if code == 132001:
        return {
            "title": "Plantilla aún no disponible",
            "message": "La plantilla seleccionada todavía no puede enviarse. Puede seguir en revisión por Meta, tener un nombre incorrecto o no estar disponible para este número de WhatsApp.",
            "technical": details,
            "code": code
        }

    if code == 131047:
        return {
            "title": "Ventana de 24 horas cerrada",
            "message": "Han pasado más de 24 horas desde el último mensaje del cliente. Usa una plantilla aprobada de WhatsApp para volver a iniciar la conversación.",
            "technical": details,
            "code": code
        }

    if code == 190:
        return {
            "title": "Token de Meta inválido",
            "message": "La conexión con Meta no está autorizada. Revisa el token de WhatsApp Cloud API.",
            "technical": details,
            "code": code
        }

    return default_result
