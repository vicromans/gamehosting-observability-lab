from datetime import date

from database.connection import get_db_connection
from services.knowledge import list_approved_documents


def list_active_beauty_services(business_id):
    """
    Return active beauty services for one business.

    The services table is the source of truth for service
    pricing, duration, deposits, warranties, and descriptions.
    """
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    service_name,
                    service_type,
                    description,
                    price,
                    currency,
                    duration_minutes,
                    requires_deposit,
                    deposit_amount,
                    warranty_days,
                    active
                FROM services
                WHERE business_id = %s
                  AND active = 1
                ORDER BY id ASC
                """,
                (business_id,),
            )

            return cursor.fetchall()

    finally:
        connection.close()


def build_beauty_ai_context(business_id):
    """
    Build public Aura Beauty context that may safely be exposed
    to the AI assistant.

    Customer appointments, phone numbers, conversation state,
    and other private customer data are intentionally excluded.
    """
    services = list_active_beauty_services(business_id)

    approved_documents = list_approved_documents(
        business_id
    )

    return {
        "business_id": business_id,
        "generated_on": date.today().isoformat(),
        "services": [
            {
                "id": service.get("id"),
                "name": service.get("service_name"),
                "description": service.get("description"),
                "price": service.get("price"),
                "currency": service.get("currency"),
                "duration_minutes": service.get(
                    "duration_minutes"
                ),
                "requires_deposit": bool(
                    service.get("requires_deposit")
                ),
                "deposit_amount": service.get(
                    "deposit_amount"
                ),
                "warranty_days": service.get(
                    "warranty_days"
                ),
            }
            for service in services
        ],
        "approved_knowledge": [
            {
                "id": document.get("id"),
                "title": document.get("title"),
                "source_type": document.get("source_type"),
                "original_filename": document.get(
                    "original_filename"
                ),
                "content": document.get("notes"),
            }
            for document in approved_documents
            if (document.get("notes") or "").strip()
        ],
    }
