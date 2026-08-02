from database.connection import get_db_connection


VALID_PROGRAM_TYPES = {
    "constellation",
    "masterclass",
    "challenge",
    "workshop",
    "retreat",
    "course",
    "other",
}

VALID_DELIVERY_MODES = {
    "presential",
    "online",
    "hybrid",
}

VALID_PROGRAM_STATUSES = {
    "draft",
    "published",
    "cancelled",
    "completed",
}

VALID_REGISTRATION_STATUSES = {
    "open",
    "closed",
    "waitlist",
}


def list_programs(business_id):
    """Return programs for one business, including their sessions."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    title,
                    program_type,
                    description,
                    delivery_mode,
                    location_name,
                    location_address,
                    online_platform,
                    online_url,
                    is_free,
                    price,
                    currency,
                    capacity,
                    registration_status,
                    registration_deadline,
                    whatsapp_group_url,
                    image_url,
                    status,
                    created_at,
                    updated_at
                FROM wellness_programs
                WHERE business_id = %s
                ORDER BY created_at DESC
                """,
                (business_id,),
            )

            programs = cursor.fetchall()

            for program in programs:
                cursor.execute(
                    """
                    SELECT
                        id,
                        program_id,
                        session_number,
                        session_title,
                        session_date,
                        start_time,
                        end_time,
                        created_at,
                        updated_at
                    FROM wellness_program_sessions
                    WHERE program_id = %s
                    ORDER BY
                        session_date ASC,
                        start_time ASC,
                        session_number ASC
                    """,
                    (program["id"],),
                )

                program["sessions"] = cursor.fetchall()

            return programs

    finally:
        connection.close()


def get_program(program_id, business_id=None):
    """Return one program and its sessions."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT *
                FROM wellness_programs
                WHERE id = %s
            """

            params = [program_id]

            if business_id is not None:
                sql += " AND business_id = %s"
                params.append(business_id)

            sql += " LIMIT 1"

            cursor.execute(sql, tuple(params))
            program = cursor.fetchone()

            if not program:
                return None

            cursor.execute(
                """
                SELECT *
                FROM wellness_program_sessions
                WHERE program_id = %s
                ORDER BY
                    session_date ASC,
                    start_time ASC,
                    session_number ASC
                """,
                (program_id,),
            )

            program["sessions"] = cursor.fetchall()
            return program

    finally:
        connection.close()


def create_program(
    business_id,
    title,
    program_type,
    description=None,
    delivery_mode="presential",
    location_name=None,
    location_address=None,
    online_platform=None,
    online_url=None,
    is_free=False,
    price=None,
    currency="MXN",
    capacity=None,
    registration_status="open",
    registration_deadline=None,
    whatsapp_group_url=None,
    image_url=None,
):
    """Create one wellness program in draft status."""

    title = (title or "").strip()
    program_type = (program_type or "").strip()
    delivery_mode = (delivery_mode or "").strip()
    registration_status = (registration_status or "").strip()

    if not title:
        raise ValueError("Program title is required")

    if program_type not in VALID_PROGRAM_TYPES:
        raise ValueError("Invalid program type")

    if delivery_mode not in VALID_DELIVERY_MODES:
        raise ValueError("Invalid delivery mode")

    if registration_status not in VALID_REGISTRATION_STATUSES:
        raise ValueError("Invalid registration status")

    if is_free:
        price = None

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wellness_programs (
                    business_id,
                    title,
                    program_type,
                    description,
                    delivery_mode,
                    location_name,
                    location_address,
                    online_platform,
                    online_url,
                    is_free,
                    price,
                    currency,
                    capacity,
                    registration_status,
                    registration_deadline,
                    whatsapp_group_url,
                    image_url,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, 'draft'
                )
                """,
                (
                    business_id,
                    title,
                    program_type,
                    description,
                    delivery_mode,
                    location_name,
                    location_address,
                    online_platform,
                    online_url,
                    1 if is_free else 0,
                    price,
                    currency,
                    capacity,
                    registration_status,
                    registration_deadline,
                    whatsapp_group_url,
                    image_url,
                ),
            )

            program_id = cursor.lastrowid

        connection.commit()
        return program_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def add_program_session(
    program_id,
    session_date,
    start_time=None,
    end_time=None,
    session_title=None,
):
    """Add one dated session to a wellness program."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(session_number), 0) + 1
                    AS next_session_number
                FROM wellness_program_sessions
                WHERE program_id = %s
                """,
                (program_id,),
            )

            row = cursor.fetchone()
            session_number = row["next_session_number"]

            cursor.execute(
                """
                INSERT INTO wellness_program_sessions (
                    program_id,
                    session_number,
                    session_title,
                    session_date,
                    start_time,
                    end_time
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    program_id,
                    session_number,
                    session_title,
                    session_date,
                    start_time,
                    end_time,
                ),
            )

            session_id = cursor.lastrowid

        connection.commit()
        return session_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_program(
    program_id,
    business_id,
    title,
    program_type,
    description=None,
    delivery_mode="presential",
    location_name=None,
    online_platform=None,
    is_free=False,
    price=None,
    currency="MXN",
    capacity=None,
):
    """Update editable fields for one wellness program."""

    title = (title or "").strip()
    program_type = (program_type or "").strip()
    delivery_mode = (delivery_mode or "").strip()

    if not title:
        raise ValueError("El título es obligatorio.")

    if program_type not in VALID_PROGRAM_TYPES:
        raise ValueError("El tipo de actividad no es válido.")

    if delivery_mode not in VALID_DELIVERY_MODES:
        raise ValueError("La modalidad no es válida.")

    if is_free:
        price = None

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_programs
                SET
                    title = %s,
                    program_type = %s,
                    description = %s,
                    delivery_mode = %s,
                    location_name = %s,
                    online_platform = %s,
                    is_free = %s,
                    price = %s,
                    currency = %s,
                    capacity = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    title,
                    program_type,
                    description,
                    delivery_mode,
                    location_name,
                    online_platform,
                    1 if is_free else 0,
                    price,
                    currency,
                    capacity,
                    program_id,
                    business_id,
                ),
            )

            updated = cursor.rowcount

        connection.commit()
        return updated > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_program_session(
    session_id,
    program_id,
    session_date,
    start_time=None,
    end_time=None,
    session_title=None,
):
    """Update one session that belongs to a wellness program."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_program_sessions
                SET
                    session_title = %s,
                    session_date = %s,
                    start_time = %s,
                    end_time = %s
                WHERE id = %s
                  AND program_id = %s
                """,
                (
                    session_title,
                    session_date,
                    start_time,
                    end_time,
                    session_id,
                    program_id,
                ),
            )

            updated = cursor.rowcount

        connection.commit()
        return updated > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_program_session(session_id, program_id):
    """Delete one session that belongs to a wellness program."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM wellness_program_sessions
                WHERE id = %s
                  AND program_id = %s
                LIMIT 1
                """,
                (
                    session_id,
                    program_id,
                ),
            )

            deleted = cursor.rowcount

        connection.commit()
        return deleted == 1

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
