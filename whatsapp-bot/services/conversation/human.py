from database.connection import get_db_connection


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
