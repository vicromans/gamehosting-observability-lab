from database.connection import get_db_connection


DEFAULT_BUSINESS_ID = 1


def get_business_by_id(business_id):
    """Return one active or inactive business by its database ID."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_name,
                    business_type,
                    owner_name,
                    phone_number,
                    active,
                    created_at
                FROM businesses
                WHERE id = %s
                LIMIT 1
                """,
                (business_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def get_default_business():
    """Return the current default business without exposing SQL to callers."""
    return get_business_by_id(DEFAULT_BUSINESS_ID)


def list_active_businesses():
    """Return every active business ordered by name."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_name,
                    business_type,
                    owner_name,
                    phone_number,
                    active,
                    created_at
                FROM businesses
                WHERE active = 1
                ORDER BY business_name ASC
                """
            )
            return cursor.fetchall()
    finally:
        connection.close()
