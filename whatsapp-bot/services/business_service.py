from database.connection import get_db_connection


DEFAULT_BUSINESS_ID = 1


BUSINESS_SELECT = """
    SELECT
        b.id,
        b.business_name,
        b.business_type,
        b.owner_name,
        b.phone_number,
        b.active,
        b.created_at,
        s.slug,
        s.email,
        s.address,
        s.timezone,
        s.opening_time,
        s.closing_time,
        s.working_days,
        s.description,
        s.founded_year,
        s.updated_at AS settings_updated_at
    FROM businesses b
    LEFT JOIN business_settings s
        ON s.business_id = b.id
"""


def get_business_by_id(business_id):
    """Return one business with its operational settings."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                {BUSINESS_SELECT}
                WHERE b.id = %s
                LIMIT 1
                """,
                (business_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def get_business_by_phone(phone_number):
    """Return one business by its registered WhatsApp phone number."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                {BUSINESS_SELECT}
                WHERE b.phone_number = %s
                LIMIT 1
                """,
                (phone_number,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def get_business_by_slug(slug):
    """Return one business by its public slug."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                {BUSINESS_SELECT}
                WHERE s.slug = %s
                LIMIT 1
                """,
                (slug,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def get_default_business():
    """Return the current default business."""
    return get_business_by_id(DEFAULT_BUSINESS_ID)


def list_active_businesses():
    """Return every active business with its settings."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                {BUSINESS_SELECT}
                WHERE b.active = 1
                ORDER BY b.business_name ASC
                """
            )
            return cursor.fetchall()
    finally:
        connection.close()
