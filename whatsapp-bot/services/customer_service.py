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


def ensure_business_customer(
    business_id,
    phone_number,
    customer_name=None,
):
    """
    Return the customer for one business/phone pair.
    Create it when it does not exist.

    This is the multi-tenant customer entry point for newer modules.
    Existing Aura-specific helpers remain unchanged for compatibility.
    """

    phone_number = (phone_number or "").strip()
    customer_name = (customer_name or "").strip() or None

    if not phone_number:
        raise ValueError("El teléfono del cliente es obligatorio.")

    variants = phone_variants(phone_number)
    placeholders = ",".join(["%s"] * len(variants))

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM customers
                WHERE business_id = %s
                  AND phone_number IN ({placeholders})
                ORDER BY last_contact DESC
                LIMIT 1
                """,
                [business_id] + variants,
            )

            customer = cursor.fetchone()

            if customer:
                cursor.execute(
                    """
                    UPDATE customers
                    SET last_contact = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (customer["id"],),
                )

                customer_id = customer["id"]

            else:
                cursor.execute(
                    """
                    INSERT INTO customers (
                        business_id,
                        phone_number,
                        customer_name
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        business_id,
                        phone_number,
                        customer_name,
                    ),
                )

                customer_id = cursor.lastrowid

        conn.commit()
        return customer_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def list_business_customers_with_session_counts(business_id):
    """Return customers for one business with wellness session counts."""

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.business_id,
                    c.phone_number,
                    c.customer_name,
                    c.preferred_name,
                    c.first_contact,
                    c.last_contact,
                    c.customer_notes,
                    COUNT(a.id) AS session_count,
                    SUM(
                        CASE
                            WHEN a.appointment_date >= CURDATE()
                             AND a.status NOT IN ('cancelled', 'canceled')
                            THEN 1
                            ELSE 0
                        END
                    ) AS upcoming_session_count
                FROM customers c
                LEFT JOIN appointments a
                    ON a.business_id = c.business_id
                   AND a.customer_phone = c.phone_number
                WHERE c.business_id = %s
                GROUP BY
                    c.id,
                    c.business_id,
                    c.phone_number,
                    c.customer_name,
                    c.preferred_name,
                    c.first_contact,
                    c.last_contact,
                    c.customer_notes
                ORDER BY c.last_contact DESC, c.id DESC
                """,
                (business_id,),
            )

            return cursor.fetchall()

    finally:
        conn.close()


def get_business_customer(customer_id, business_id):
    """Return one customer belonging to one business."""

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    phone_number,
                    customer_name,
                    preferred_name,
                    first_contact,
                    last_contact,
                    customer_notes
                FROM customers
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
                """,
                (
                    customer_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        conn.close()


def list_business_customer_appointments(
    business_id,
    phone_number,
):
    """Return the wellness appointment history for one customer."""

    variants = phone_variants(phone_number)
    placeholders = ",".join(["%s"] * len(variants))

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    id,
                    service_name,
                    appointment_date,
                    appointment_time,
                    duration_minutes,
                    delivery_mode,
                    status,
                    notes,
                    created_at
                FROM appointments
                WHERE business_id = %s
                  AND customer_phone IN ({placeholders})
                ORDER BY
                    appointment_date DESC,
                    appointment_time DESC,
                    id DESC
                """,
                [business_id] + variants,
            )

            return cursor.fetchall()

    finally:
        conn.close()


def update_business_customer(
    customer_id,
    business_id,
    customer_name,
    preferred_name=None,
    phone_number=None,
    customer_notes=None,
):
    """Update one business customer and preserve appointment linkage."""

    customer_name = (customer_name or "").strip()
    preferred_name = (preferred_name or "").strip() or None
    phone_number = (phone_number or "").strip()
    customer_notes = (customer_notes or "").strip() or None

    if not customer_name:
        raise ValueError("El nombre del cliente es obligatorio.")

    if not phone_number:
        raise ValueError("El teléfono del cliente es obligatorio.")

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    phone_number
                FROM customers
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
                """,
                (
                    customer_id,
                    business_id,
                ),
            )

            customer = cursor.fetchone()

            if not customer:
                raise ValueError("El cliente no existe.")

            old_phone = customer["phone_number"]

            cursor.execute(
                """
                SELECT id
                FROM customers
                WHERE business_id = %s
                  AND phone_number = %s
                  AND id <> %s
                LIMIT 1
                """,
                (
                    business_id,
                    phone_number,
                    customer_id,
                ),
            )

            duplicate = cursor.fetchone()

            if duplicate:
                raise ValueError(
                    "Ya existe otro cliente con ese teléfono."
                )

            cursor.execute(
                """
                UPDATE customers
                SET
                    customer_name = %s,
                    preferred_name = %s,
                    phone_number = %s,
                    customer_notes = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    customer_name,
                    preferred_name,
                    phone_number,
                    customer_notes,
                    customer_id,
                    business_id,
                ),
            )

            if phone_number != old_phone:
                cursor.execute(
                    """
                    UPDATE appointments
                    SET customer_phone = %s
                    WHERE business_id = %s
                      AND customer_phone = %s
                    """,
                    (
                        phone_number,
                        business_id,
                        old_phone,
                    ),
                )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def list_business_customer_program_registrations(
    business_id,
    customer_id,
):
    """Return wellness program registrations for one customer."""

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id AS registration_id,
                    r.program_id,
                    r.registration_status,
                    r.payment_status,
                    r.amount_paid,
                    r.notes AS registration_notes,
                    r.registered_at,
                    r.updated_at,

                    p.title AS program_title,
                    p.program_type,
                    p.delivery_mode,
                    p.location_name,
                    p.online_platform,
                    p.price AS program_price,
                    p.currency,
                    p.is_free,
                    p.status AS program_status

                FROM wellness_program_registrations r

                INNER JOIN wellness_programs p
                    ON p.id = r.program_id
                   AND p.business_id = r.business_id

                WHERE r.business_id = %s
                  AND r.customer_id = %s

                ORDER BY
                    r.registered_at DESC,
                    r.id DESC
                """,
                (
                    business_id,
                    customer_id,
                ),
            )

            return cursor.fetchall()

    finally:
        conn.close()
