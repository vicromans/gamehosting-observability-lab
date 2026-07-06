from database.connection import get_db_connection
from services.utils.phone import phone_variants


def find_customer_by_phone(phone_number):
    variants = phone_variants(phone_number)
    placeholders = ",".join(["%s"] * len(variants))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT *
        FROM customers
        WHERE business_id = %s
          AND phone_number IN ({placeholders})
        ORDER BY last_contact DESC
        LIMIT 1
    """, [1] + variants)

    customer = cursor.fetchone()
    cursor.close()
    conn.close()
    return customer


def get_customer_display_name(phone_number):
    customer = find_customer_by_phone(phone_number)

    if not customer:
        return None

    return (
        customer.get("preferred_name")
        or customer.get("customer_name")
        or None
    )


def customer_can_home_service(phone_number):
    customer = find_customer_by_phone(phone_number)
    return bool(customer and customer.get("can_home_service"))


def customer_has_future_appointment(phone_number):
    variants = phone_variants(phone_number)
    placeholders = ",".join(["%s"] * len(variants))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id
        FROM appointments
        WHERE business_id = %s
          AND customer_phone IN ({placeholders})
          AND appointment_date >= CURDATE()
          AND status != 'canceled'
        ORDER BY appointment_date ASC, appointment_time ASC
        LIMIT 1
    """, [1] + variants)

    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return bool(row)
