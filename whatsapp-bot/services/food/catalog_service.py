from database.connection import get_db_connection


CATALOG_FIELDS = """
    id,
    business_id,
    item_name,
    category,
    subcategory,
    description,
    included_in_meal,
    has_surcharge,
    surcharge_amount,
    available_individually,
    individual_price,
    currency,
    active,
    display_order,
    created_at,
    updated_at
"""


def list_catalog_items(business_id, include_inactive=False):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            query = f"""
                SELECT {CATALOG_FIELDS}
                FROM food_catalog_items
                WHERE business_id = %s
            """
            params = [business_id]

            if not include_inactive:
                query += " AND active = 1"

            query += """
                ORDER BY
                    category ASC,
                    subcategory ASC,
                    display_order ASC,
                    item_name ASC
            """

            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def get_catalog_item(business_id, item_id):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {CATALOG_FIELDS}
                FROM food_catalog_items
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
                """,
                (item_id, business_id),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def create_catalog_item(
    business_id,
    item_name,
    category=None,
    subcategory=None,
    description=None,
    included_in_meal=True,
    has_surcharge=False,
    surcharge_amount=None,
    available_individually=False,
    individual_price=None,
    currency="MXN",
    active=True,
    display_order=0,
):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO food_catalog_items (
                    business_id,
                    item_name,
                    category,
                    subcategory,
                    description,
                    included_in_meal,
                    has_surcharge,
                    surcharge_amount,
                    available_individually,
                    individual_price,
                    currency,
                    active,
                    display_order
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    business_id,
                    item_name,
                    category,
                    subcategory,
                    description,
                    1 if included_in_meal else 0,
                    1 if has_surcharge else 0,
                    surcharge_amount,
                    1 if available_individually else 0,
                    individual_price,
                    currency,
                    1 if active else 0,
                    display_order,
                ),
            )
            item_id = cursor.lastrowid

        connection.commit()
        return item_id
    finally:
        connection.close()


def update_catalog_item(
    business_id,
    item_id,
    item_name,
    category=None,
    subcategory=None,
    description=None,
    included_in_meal=True,
    has_surcharge=False,
    surcharge_amount=None,
    available_individually=False,
    individual_price=None,
    currency="MXN",
    active=True,
    display_order=0,
):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE food_catalog_items
                SET
                    item_name = %s,
                    category = %s,
                    subcategory = %s,
                    description = %s,
                    included_in_meal = %s,
                    has_surcharge = %s,
                    surcharge_amount = %s,
                    available_individually = %s,
                    individual_price = %s,
                    currency = %s,
                    active = %s,
                    display_order = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    item_name,
                    category,
                    subcategory,
                    description,
                    1 if included_in_meal else 0,
                    1 if has_surcharge else 0,
                    surcharge_amount,
                    1 if available_individually else 0,
                    individual_price,
                    currency,
                    1 if active else 0,
                    display_order,
                    item_id,
                    business_id,
                ),
            )
            updated = cursor.rowcount

        connection.commit()
        return updated == 1
    finally:
        connection.close()


def set_catalog_item_active(business_id, item_id, active):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE food_catalog_items
                SET active = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (1 if active else 0, item_id, business_id),
            )
            updated = cursor.rowcount

        connection.commit()
        return updated == 1
    finally:
        connection.close()


def delete_catalog_item(business_id, item_id):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM food_catalog_items
                WHERE id = %s
                  AND business_id = %s
                """,
                (item_id, business_id),
            )
            deleted = cursor.rowcount

        connection.commit()
        return deleted == 1
    finally:
        connection.close()
