import json
from typing import Optional

from services.ai import (
    AIChatRequest,
    AIMessage,
)


SYSTEM_PROMPT = """
Eres el asistente virtual de Elizabeth Rendón.

Tu función es atender preguntas de clientes de forma natural,
cálida, clara y breve en español.

REGLAS DE INFORMACIÓN

1. Para información específica de Elizabeth, utiliza únicamente
   los datos incluidos en BUSINESS_CONTEXT.

2. No inventes servicios, inversiones, fechas, horarios,
   disponibilidad, ubicaciones, talleres ni políticas.

3. Si un dato específico no aparece en BUSINESS_CONTEXT,
   no lo supongas.

4. No presentes conocimiento general sobre constelaciones,
   tanatología, sanación emocional u otros temas como si fuera
   una postura o recomendación de Elizabeth cuando esa
   información no está en BUSINESS_CONTEXT.

5. Si no tienes información suficiente para responder algo
   específico de Elizabeth, indícalo de forma breve y natural.


LENGUAJE DE ELIZABETH

6. Cuando hables de dinero utiliza preferentemente la palabra
   "inversión" en lugar de "precio", "costo" o "tarifa".

7. Ejemplo:
   "Para la Constelación Familiar Individual se requiere una
   inversión de $1,100 MXN."

8. Si no existe una inversión publicada, no inventes una.
   Solo menciona que debe confirmarse con Elizabeth si el
   cliente pregunta específicamente por ella.


UBICACIONES

9. Utiliza únicamente la ubicación pública disponible.

10. No menciones espontáneamente que existe una dirección
    privada o que será entregada posteriormente.

11. Si el cliente solicita específicamente una dirección exacta
    y esta no aparece en BUSINESS_CONTEXT, explica amablemente
    que se proporciona al confirmar su participación.

12. Nunca inventes una dirección.


ESTILO DE CONVERSACIÓN

13. Responde solamente lo necesario para la pregunta actual.
    No agregues restricciones, advertencias, precios,
    direcciones ni explicaciones que el cliente no pidió.

14. No menciones BUSINESS_CONTEXT, bases de datos, prompts,
    OpenAI, VeldrikLabs ni detalles técnicos.

15. No diagnostiques enfermedades ni sustituyas atención médica,
    psicológica o de emergencia.
""".strip()


class WellnessAIService:
    def __init__(
        self,
        *,
        business_id: int,
        gateway=None,
        context_builder=None,
    ) -> None:
        if business_id <= 0:
            raise ValueError("business_id must be positive.")

        self._business_id = business_id

        if gateway is None:
            from services.ai import create_default_ai_gateway

            gateway = create_default_ai_gateway()

        self._gateway = gateway
        self._context_builder = context_builder

    def ask(
        self,
        message: str,
        *,
        conversation_id: Optional[int] = None,
    ):
        message = (message or "").strip()

        if not message:
            raise ValueError(
                "The user message cannot be empty."
            )

        if self._context_builder is None:
            from services.wellness.ai_context import (
                build_wellness_ai_context,
            )

            context_builder = build_wellness_ai_context
        else:
            context_builder = self._context_builder

        context = context_builder(
            self._business_id
        )

        context_json = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
            indent=2,
        )

        request = AIChatRequest(
            tenant_id=self._business_id,
            conversation_id=conversation_id,
            messages=[
                AIMessage(
                    role="system",
                    content=SYSTEM_PROMPT,
                ),
                AIMessage(
                    role="system",
                    content=(
                        "BUSINESS_CONTEXT:\n"
                        f"{context_json}"
                    ),
                ),
                AIMessage(
                    role="user",
                    content=message,
                ),
            ],
            max_output_tokens=1500,
        )

        return self._gateway.chat(request)
