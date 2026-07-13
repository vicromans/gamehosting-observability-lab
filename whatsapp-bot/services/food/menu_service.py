from database.connection import get_db_connection


def get_menu_by_date(business_id, menu_date):
    """Return one daily menu with all of its items."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    menu_date,
                    title,
                    intro_text,
                    image_url,
                    status,
                    published_at,
                    created_at,
                    updated_at
                FROM daily_menus
                WHERE business_id = %s
                  AND menu_date = %s
                LIMIT 1
                """,
                (business_id, menu_date),
            )
            menu = cursor.fetchone()

            if not menu:
                return None

            cursor.execute(
                """
                SELECT
                    id,
                    daily_menu_id,
                    item_name,
                    category,
                    description,
                    price,
                    currency,
                    available,
                    display_order,
                    created_at,
                    updated_at
                FROM daily_menu_items
                WHERE daily_menu_id = %s
                ORDER BY display_order ASC, id ASC
                """,
                (menu["id"],),
            )
            menu["items"] = cursor.fetchall()

            return menu
    finally:
        connection.close()


def create_or_update_menu(
    business_id,
    menu_date,
    title=None,
    intro_text=None,
    image_url=None,
    status="draft",
):
    """Create or update one menu for a business and date."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_menus (
                    business_id,
                    menu_date,
                    title,
                    intro_text,
                    image_url,
                    status,
                    published_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CASE
                        WHEN %s = 'published' THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                )
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    intro_text = VALUES(intro_text),
                    image_url = VALUES(image_url),
                    status = VALUES(status),
                    published_at = CASE
                        WHEN VALUES(status) = 'published'
                            THEN COALESCE(published_at, CURRENT_TIMESTAMP)
                        ELSE NULL
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    business_id,
                    menu_date,
                    title,
                    intro_text,
                    image_url,
                    status,
                    status,
                ),
            )

            cursor.execute(
                """
                SELECT id
                FROM daily_menus
                WHERE business_id = %s
                  AND menu_date = %s
                LIMIT 1
                """,
                (business_id, menu_date),
            )
            menu = cursor.fetchone()

        connection.commit()
        return menu["id"]
    finally:
        connection.close()


def add_menu_item(
    daily_menu_id,
    item_name,
    category=None,
    description=None,
    price=None,
    currency="MXN",
    available=True,
    display_order=0,
):
    """Add one item to a daily menu."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_menu_items (
                    daily_menu_id,
                    item_name,
                    category,
                    description,
                    price,
                    currency,
                    available,
                    display_order
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    daily_menu_id,
                    item_name,
                    category,
                    description,
                    price,
                    currency,
                    1 if available else 0,
                    display_order,
                ),
            )
            item_id = cursor.lastrowid

        connection.commit()
        return item_id
    finally:
        connection.close()


def set_menu_item_availability(item_id, available):
    """Mark one menu item as available or unavailable."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE daily_menu_items
                SET available = %s
                WHERE id = %s
                """,
                (1 if available else 0, item_id),
            )
            updated = cursor.rowcount

        connection.commit()
        return updated == 1
    finally:
        connection.close()
