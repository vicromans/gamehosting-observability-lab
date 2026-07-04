from database.connection import get_db_connection
from services.notifications.owner_notifications import notify_human_request


def mark_human_required(phone_number):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE customers
                SET human_required = TRUE,
                    last_contact = CURRENT_TIMESTAMP
                WHERE phone_number = %s
            """, (phone_number,))

        connection.commit()
    finally:
        connection.close()


def clear_human_required(phone_number):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE customers
                SET human_required = FALSE,
                    last_contact = CURRENT_TIMESTAMP
                WHERE phone_number = %s
            """, (phone_number,))

        connection.commit()
    finally:
        connection.close()


def handle_human_request(phone_number, incoming_message=None, customer_name=None):
    mark_human_required(phone_number)
    notify_human_request(
        phone_number,
        customer_name=customer_name,
        incoming_message=incoming_message
    )


def is_human_required(phone_number):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT human_required
                FROM customers
                WHERE phone_number = %s
                LIMIT 1
            """, (phone_number,))
            row = cursor.fetchone()

            if not row:
                return False

            return bool(row.get("human_required"))
    finally:
        connection.close()
