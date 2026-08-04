from datetime import date, datetime, time, timedelta

from database.connection import get_db_connection
from services.customer_service import ensure_business_customer


VALID_DELIVERY_MODES = {
    "presential",
    "online",
    "hybrid",
}


def list_session_types(business_id, include_inactive=False):
    """Return individual session types for one business."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    id,
                    business_id,
                    name,
                    description,
                    duration_minutes,
                    price,
                    currency,
                    delivery_mode,
                    active,
                    display_order,
                    created_at,
                    updated_at
                FROM wellness_session_types
                WHERE business_id = %s
            """

            params = [business_id]

            if not include_inactive:
                sql += " AND active = 1"

            sql += """
                ORDER BY
                    display_order ASC,
                    name ASC
            """

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    finally:
        connection.close()


def create_session_type(
    business_id,
    name,
    duration_minutes,
    description=None,
    price=None,
    currency="MXN",
    delivery_mode="presential",
):
    """Create one individual session type."""

    name = (name or "").strip()
    delivery_mode = (delivery_mode or "").strip()

    if not name:
        raise ValueError("El nombre de la sesión es obligatorio.")

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise ValueError("La duración no es válida.")

    if duration_minutes <= 0:
        raise ValueError("La duración debe ser mayor que cero.")

    if delivery_mode not in VALID_DELIVERY_MODES:
        raise ValueError("La modalidad no es válida.")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wellness_session_types (
                    business_id,
                    name,
                    description,
                    duration_minutes,
                    price,
                    currency,
                    delivery_mode,
                    active
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, 1
                )
                """,
                (
                    business_id,
                    name,
                    description,
                    duration_minutes,
                    price,
                    currency,
                    delivery_mode,
                ),
            )

            session_type_id = cursor.lastrowid

        connection.commit()
        return session_type_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def list_availability(business_id):
    """Return weekly availability ranges for one business."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    weekday,
                    start_time,
                    end_time,
                    active,
                    created_at,
                    updated_at
                FROM wellness_availability
                WHERE business_id = %s
                  AND active = 1
                ORDER BY
                    weekday ASC,
                    start_time ASC
                """,
                (business_id,),
            )

            return cursor.fetchall()

    finally:
        connection.close()


def add_availability_range(
    business_id,
    weekday,
    start_time,
    end_time,
):
    """Add one recurring weekly availability range."""

    try:
        weekday = int(weekday)
    except (TypeError, ValueError):
        raise ValueError("El día de la semana no es válido.")

    if weekday < 0 or weekday > 6:
        raise ValueError("El día de la semana no es válido.")

    if not start_time or not end_time:
        raise ValueError("La hora de inicio y término son obligatorias.")

    if end_time <= start_time:
        raise ValueError(
            "La hora de término debe ser posterior a la hora de inicio."
        )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wellness_availability (
                    business_id,
                    weekday,
                    start_time,
                    end_time,
                    active
                )
                VALUES (%s, %s, %s, %s, 1)
                """,
                (
                    business_id,
                    weekday,
                    start_time,
                    end_time,
                ),
            )

            availability_id = cursor.lastrowid

        connection.commit()
        return availability_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_session_type(session_type_id, business_id):
    """Return one active wellness session type for a business."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    name,
                    description,
                    duration_minutes,
                    price,
                    currency,
                    delivery_mode,
                    active
                FROM wellness_session_types
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                LIMIT 1
                """,
                (
                    session_type_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def list_wellness_appointments(
    business_id,
    start_date=None,
    end_date=None,
):
    """Return wellness appointments for one business."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    a.id,
                    a.business_id,
                    a.customer_phone,
                    a.customer_name,
                    a.service_name,
                    a.session_type_id,
                    a.appointment_date,
                    a.appointment_time,
                    a.duration_minutes,
                    a.delivery_mode,
                    a.status,
                    a.notes,
                    a.created_at,
                    st.name AS session_type_name
                FROM appointments a
                LEFT JOIN wellness_session_types st
                    ON st.id = a.session_type_id
                   AND st.business_id = a.business_id
                WHERE a.business_id = %s
            """

            params = [business_id]

            if start_date is not None:
                sql += " AND a.appointment_date >= %s"
                params.append(start_date)

            if end_date is not None:
                sql += " AND a.appointment_date <= %s"
                params.append(end_date)

            sql += """
                ORDER BY
                    a.appointment_date ASC,
                    a.appointment_time ASC
            """

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    finally:
        connection.close()


def create_wellness_appointment(
    business_id,
    session_type_id,
    customer_name,
    customer_phone,
    appointment_date,
    appointment_time,
    status="pending",
    notes=None,
):
    """Create one wellness appointment using a session type snapshot."""

    session_type = get_session_type(
        session_type_id,
        business_id,
    )

    if not session_type:
        raise ValueError("El tipo de sesión no existe o está inactivo.")

    customer_name = (customer_name or "").strip()
    customer_phone = (customer_phone or "").strip()

    if not customer_name:
        raise ValueError("El nombre del cliente es obligatorio.")

    if not customer_phone:
        raise ValueError("El teléfono del cliente es obligatorio.")

    if not appointment_date:
        raise ValueError("La fecha es obligatoria.")

    if not appointment_time:
        raise ValueError("La hora es obligatoria.")

    validate_wellness_appointment_slot(
        business_id=business_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        duration_minutes=session_type["duration_minutes"],
    )

    ensure_business_customer(
        business_id=business_id,
        phone_number=customer_phone,
        customer_name=customer_name,
    )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO appointments (
                    business_id,
                    customer_phone,
                    service_location,
                    customer_name,
                    service_name,
                    session_type_id,
                    appointment_date,
                    appointment_time,
                    duration_minutes,
                    delivery_mode,
                    status,
                    deposit_required,
                    deposit_paid,
                    notes
                )
                VALUES (
                    %s, %s, NULL, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    NULL, 0, %s
                )
                """,
                (
                    business_id,
                    customer_phone,
                    customer_name,
                    session_type["name"],
                    session_type["id"],
                    appointment_date,
                    appointment_time,
                    session_type["duration_minutes"],
                    session_type["delivery_mode"],
                    status,
                    notes,
                ),
            )

            appointment_id = cursor.lastrowid

        connection.commit()
        return appointment_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_session_type(
    session_type_id,
    business_id,
    name,
    duration_minutes,
    description=None,
    price=None,
    currency="MXN",
    delivery_mode="presential",
):
    """Update one active wellness session type."""

    name = (name or "").strip()
    delivery_mode = (delivery_mode or "").strip()

    if not name:
        raise ValueError("El nombre de la sesión es obligatorio.")

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise ValueError("La duración no es válida.")

    if duration_minutes <= 0:
        raise ValueError("La duración debe ser mayor que cero.")

    if delivery_mode not in VALID_DELIVERY_MODES:
        raise ValueError("La modalidad no es válida.")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_session_types
                SET
                    name = %s,
                    description = %s,
                    duration_minutes = %s,
                    price = %s,
                    currency = %s,
                    delivery_mode = %s
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                """,
                (
                    name,
                    description,
                    duration_minutes,
                    price,
                    currency,
                    delivery_mode,
                    session_type_id,
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


def get_availability_range(availability_id, business_id):
    """Return one active availability range for a business."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    weekday,
                    start_time,
                    end_time,
                    active
                FROM wellness_availability
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                LIMIT 1
                """,
                (
                    availability_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def update_availability_range(
    availability_id,
    business_id,
    weekday,
    start_time,
    end_time,
):
    """Update one recurring weekly availability range."""

    try:
        weekday = int(weekday)
    except (TypeError, ValueError):
        raise ValueError("El día de la semana no es válido.")

    if weekday < 0 or weekday > 6:
        raise ValueError("El día de la semana no es válido.")

    if not start_time or not end_time:
        raise ValueError(
            "La hora de inicio y término son obligatorias."
        )

    if end_time <= start_time:
        raise ValueError(
            "La hora de término debe ser posterior a la hora de inicio."
        )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_availability
                SET
                    weekday = %s,
                    start_time = %s,
                    end_time = %s
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                """,
                (
                    weekday,
                    start_time,
                    end_time,
                    availability_id,
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


def delete_availability_range(
    availability_id,
    business_id,
):
    """Soft-delete one recurring weekly availability range."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_availability
                SET active = 0
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                """,
                (
                    availability_id,
                    business_id,
                ),
            )

            deleted = cursor.rowcount

        connection.commit()
        return deleted > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_session_type(
    session_type_id,
    business_id,
):
    """Soft-delete one wellness session type."""
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_session_types
                SET active = 0
                WHERE id = %s
                  AND business_id = %s
                  AND active = 1
                """,
                (
                    session_type_id,
                    business_id,
                ),
            )

            deleted = cursor.rowcount

        connection.commit()
        return deleted > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_wellness_appointment(appointment_id, business_id):
    """Return one wellness appointment belonging to one business."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.business_id,
                    a.customer_phone,
                    a.customer_name,
                    a.service_name,
                    a.session_type_id,
                    a.appointment_date,
                    a.appointment_time,
                    a.duration_minutes,
                    a.delivery_mode,
                    a.status,
                    a.notes,
                    a.created_at,
                    st.name AS session_type_name
                FROM appointments a
                LEFT JOIN wellness_session_types st
                    ON st.id = a.session_type_id
                   AND st.business_id = a.business_id
                WHERE a.id = %s
                  AND a.business_id = %s
                LIMIT 1
                """,
                (
                    appointment_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def update_wellness_appointment(
    appointment_id,
    business_id,
    session_type_id,
    customer_name,
    customer_phone,
    appointment_date,
    appointment_time,
    status="pending",
    notes=None,
):
    """Update a wellness appointment and refresh its session snapshot."""

    appointment = get_wellness_appointment(
        appointment_id,
        business_id,
    )

    if not appointment:
        raise ValueError("La sesión no existe.")

    session_type = get_session_type(
        session_type_id,
        business_id,
    )

    if not session_type:
        raise ValueError("El tipo de sesión no existe o está inactivo.")

    customer_name = (customer_name or "").strip()
    customer_phone = (customer_phone or "").strip()
    notes = (notes or "").strip() or None

    if not customer_name:
        raise ValueError("El nombre del cliente es obligatorio.")

    if not customer_phone:
        raise ValueError("El teléfono del cliente es obligatorio.")

    if not appointment_date:
        raise ValueError("La fecha es obligatoria.")

    if not appointment_time:
        raise ValueError("La hora es obligatoria.")

    valid_statuses = {
        "pending",
        "confirmed",
        "completed",
        "cancelled",
    }

    if status not in valid_statuses:
        raise ValueError("El estado de la sesión no es válido.")

    if status in {"pending", "confirmed"}:
        validate_wellness_appointment_slot(
            business_id=business_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=session_type["duration_minutes"],
            exclude_appointment_id=appointment_id,
        )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE appointments
                SET
                    customer_phone = %s,
                    customer_name = %s,
                    service_name = %s,
                    session_type_id = %s,
                    appointment_date = %s,
                    appointment_time = %s,
                    duration_minutes = %s,
                    delivery_mode = %s,
                    status = %s,
                    notes = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    customer_phone,
                    customer_name,
                    session_type["name"],
                    session_type_id,
                    appointment_date,
                    appointment_time,
                    session_type["duration_minutes"],
                    session_type["delivery_mode"],
                    status,
                    notes,
                    appointment_id,
                    business_id,
                ),
            )

        connection.commit()

    finally:
        connection.close()


def list_schedule_blocks(
    business_id,
    start_date=None,
    end_date=None,
):
    """Return schedule blocks for one wellness business."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    id,
                    business_id,
                    blocked_date,
                    start_time,
                    end_time,
                    reason,
                    created_at
                FROM wellness_schedule_blocks
                WHERE business_id = %s
            """

            params = [business_id]

            if start_date is not None:
                sql += " AND blocked_date >= %s"
                params.append(start_date)

            if end_date is not None:
                sql += " AND blocked_date <= %s"
                params.append(end_date)

            sql += """
                ORDER BY
                    blocked_date ASC,
                    start_time ASC
            """

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    finally:
        connection.close()


def get_schedule_block(
    block_id,
    business_id,
):
    """Return one wellness schedule block."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    business_id,
                    blocked_date,
                    start_time,
                    end_time,
                    reason,
                    created_at
                FROM wellness_schedule_blocks
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
                """,
                (
                    block_id,
                    business_id,
                ),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def create_schedule_block(
    business_id,
    blocked_date,
    start_time=None,
    end_time=None,
    reason=None,
):
    """Create a full-day or partial wellness schedule block."""

    if not blocked_date:
        raise ValueError("La fecha es obligatoria.")

    reason = (reason or "").strip() or None

    if bool(start_time) != bool(end_time):
        raise ValueError(
            "Para un bloqueo parcial debes indicar "
            "hora de inicio y hora de término."
        )

    if start_time and end_time:
        if end_time <= start_time:
            raise ValueError(
                "La hora de término debe ser posterior "
                "a la hora de inicio."
            )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wellness_schedule_blocks (
                    business_id,
                    blocked_date,
                    start_time,
                    end_time,
                    reason
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    blocked_date,
                    start_time,
                    end_time,
                    reason,
                ),
            )

            block_id = cursor.lastrowid

        connection.commit()
        return block_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_schedule_block(
    block_id,
    business_id,
    blocked_date,
    start_time=None,
    end_time=None,
    reason=None,
):
    """Update one wellness schedule block."""

    block = get_schedule_block(
        block_id,
        business_id,
    )

    if not block:
        raise ValueError("El bloqueo no existe.")

    if not blocked_date:
        raise ValueError("La fecha es obligatoria.")

    reason = (reason or "").strip() or None

    if bool(start_time) != bool(end_time):
        raise ValueError(
            "Para un bloqueo parcial debes indicar "
            "hora de inicio y hora de término."
        )

    if start_time and end_time:
        if end_time <= start_time:
            raise ValueError(
                "La hora de término debe ser posterior "
                "a la hora de inicio."
            )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE wellness_schedule_blocks
                SET
                    blocked_date = %s,
                    start_time = %s,
                    end_time = %s,
                    reason = %s
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    blocked_date,
                    start_time,
                    end_time,
                    reason,
                    block_id,
                    business_id,
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_schedule_block(
    block_id,
    business_id,
):
    """Delete one wellness schedule block."""

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM wellness_schedule_blocks
                WHERE id = %s
                  AND business_id = %s
                """,
                (
                    block_id,
                    business_id,
                ),
            )

            deleted = cursor.rowcount

        connection.commit()
        return deleted > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _wellness_date_value(value):
    """Normalize a date or YYYY-MM-DD string to date."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return datetime.strptime(
            str(value),
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        raise ValueError("La fecha no es válida.")


def _wellness_time_seconds(value):
    """Normalize MariaDB TIME, datetime.time or HH:MM string to seconds."""
    if value is None:
        return None

    if isinstance(value, timedelta):
        return int(value.total_seconds())

    if isinstance(value, time):
        return (
            value.hour * 3600
            + value.minute * 60
            + value.second
        )

    raw = str(value).strip()

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            return (
                parsed.hour * 3600
                + parsed.minute * 60
                + parsed.second
            )
        except ValueError:
            pass

    raise ValueError("La hora no es válida.")


def validate_wellness_appointment_slot(
    business_id,
    appointment_date,
    appointment_time,
    duration_minutes,
    exclude_appointment_id=None,
):
    """
    Validate one wellness appointment against:
    - weekly availability
    - full-day / partial schedule blocks
    - other appointments
    """

    appointment_date = _wellness_date_value(
        appointment_date
    )

    start_seconds = _wellness_time_seconds(
        appointment_time
    )

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise ValueError("La duración de la sesión no es válida.")

    if duration_minutes <= 0:
        raise ValueError("La duración de la sesión no es válida.")

    end_seconds = (
        start_seconds
        + duration_minutes * 60
    )

    if end_seconds > 24 * 3600:
        raise ValueError(
            "La sesión no puede terminar después de medianoche."
        )

    weekday = appointment_date.weekday()

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            # 1. Weekly availability
            cursor.execute(
                """
                SELECT
                    start_time,
                    end_time
                FROM wellness_availability
                WHERE business_id = %s
                  AND weekday = %s
                  AND active = 1
                ORDER BY start_time
                """,
                (
                    business_id,
                    weekday,
                ),
            )

            availability_ranges = cursor.fetchall()

            fits_availability = False

            for row in availability_ranges:
                available_start = _wellness_time_seconds(
                    row["start_time"]
                )
                available_end = _wellness_time_seconds(
                    row["end_time"]
                )

                if (
                    start_seconds >= available_start
                    and end_seconds <= available_end
                ):
                    fits_availability = True
                    break

            if not fits_availability:
                raise ValueError(
                    "Ese horario está fuera de la "
                    "disponibilidad configurada."
                )

            # 2. Full-day / partial blocks
            cursor.execute(
                """
                SELECT
                    start_time,
                    end_time,
                    reason
                FROM wellness_schedule_blocks
                WHERE business_id = %s
                  AND blocked_date = %s
                """,
                (
                    business_id,
                    appointment_date,
                ),
            )

            blocks = cursor.fetchall()

            for block in blocks:

                # NULL / NULL means full day.
                if (
                    block["start_time"] is None
                    and block["end_time"] is None
                ):
                    raise ValueError(
                        "Ese día está bloqueado en la agenda."
                    )

                block_start = _wellness_time_seconds(
                    block["start_time"]
                )
                block_end = _wellness_time_seconds(
                    block["end_time"]
                )

                if (
                    start_seconds < block_end
                    and end_seconds > block_start
                ):
                    raise ValueError(
                        "Ese horario coincide con un "
                        "bloqueo de agenda."
                    )

            # 3. Existing appointments
            sql = """
                SELECT
                    id,
                    appointment_time,
                    duration_minutes,
                    customer_name
                FROM appointments
                WHERE business_id = %s
                  AND appointment_date = %s
                  AND status NOT IN (
                      'cancelled',
                      'canceled'
                  )
            """

            params = [
                business_id,
                appointment_date,
            ]

            if exclude_appointment_id is not None:
                sql += " AND id <> %s"
                params.append(exclude_appointment_id)

            cursor.execute(sql, tuple(params))
            appointments = cursor.fetchall()

            for existing in appointments:
                if existing["appointment_time"] is None:
                    continue

                existing_start = _wellness_time_seconds(
                    existing["appointment_time"]
                )

                existing_duration = (
                    existing["duration_minutes"] or 0
                )

                existing_end = (
                    existing_start
                    + int(existing_duration) * 60
                )

                if (
                    start_seconds < existing_end
                    and end_seconds > existing_start
                ):
                    raise ValueError(
                        "Ese horario se empalma con "
                        "otra sesión agendada."
                    )

        return True

    finally:
        connection.close()
