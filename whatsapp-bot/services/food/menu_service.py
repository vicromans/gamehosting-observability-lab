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


def remove_menu_item(item_id):
    """Remove one item from a daily menu."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM daily_menu_items
                WHERE id = %s
                LIMIT 1
                """,
                (item_id,),
            )
            deleted = cursor.rowcount

        connection.commit()
        return deleted == 1

    finally:
        connection.close()


def add_catalog_items_to_menu(
    business_id,
    menu_date,
    catalog_item_ids,
):
    """
    Create the daily menu when necessary and copy selected catalog
    items into it.

    The copied values preserve the historical state of the menu even
    if the catalog changes later.
    """
    normalized_ids = []

    for item_id in catalog_item_ids:
        try:
            normalized_id = int(item_id)
        except (TypeError, ValueError):
            continue

        if normalized_id > 0 and normalized_id not in normalized_ids:
            normalized_ids.append(normalized_id)

    if not normalized_ids:
        return 0

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_menus (
                    business_id,
                    menu_date,
                    title,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    'draft'
                )
                ON DUPLICATE KEY UPDATE
                    updated_at = updated_at
                """,
                (
                    business_id,
                    menu_date,
                    "Menú del día",
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

            if not menu:
                connection.rollback()
                return 0

            placeholders = ", ".join(["%s"] * len(normalized_ids))

            cursor.execute(
                f"""
                SELECT
                    id,
                    item_name,
                    category,
                    description,
                    available_individually,
                    individual_price,
                    currency,
                    display_order
                FROM food_catalog_items
                WHERE business_id = %s
                  AND active = 1
                  AND id IN ({placeholders})
                ORDER BY
                    category ASC,
                    display_order ASC,
                    item_name ASC
                """,
                [business_id, *normalized_ids],
            )
            catalog_items = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    item_name,
                    category
                FROM daily_menu_items
                WHERE daily_menu_id = %s
                """,
                (menu["id"],),
            )
            existing_items = {
                (
                    (item.get("item_name") or "").strip().casefold(),
                    (item.get("category") or "").strip().casefold(),
                )
                for item in cursor.fetchall()
            }

            added = 0

            for item in catalog_items:
                duplicate_key = (
                    (item.get("item_name") or "").strip().casefold(),
                    (item.get("category") or "").strip().casefold(),
                )

                if duplicate_key in existing_items:
                    continue

                price = None

                if item.get("available_individually"):
                    price = item.get("individual_price")

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
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        1,
                        %s
                    )
                    """,
                    (
                        menu["id"],
                        item.get("item_name"),
                        item.get("category"),
                        item.get("description"),
                        price,
                        item.get("currency") or "MXN",
                        item.get("display_order") or 0,
                    ),
                )

                existing_items.add(duplicate_key)
                added += 1

        connection.commit()
        return added

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
