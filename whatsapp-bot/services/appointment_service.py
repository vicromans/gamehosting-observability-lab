from datetime import datetime
from zoneinfo import ZoneInfo

from database.connection import get_db_connection


DEFAULT_AVAILABLE_TIMES = ["10:00:00", "12:00:00", "15:00:00"]


def get_business_time_slots(appointment_date, business_id=1):
    weekday = datetime.strptime(str(appointment_date), "%Y-%m-%d").weekday()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT slot_time, active
        FROM business_time_slots
        WHERE business_id = %s
          AND weekday = %s
        ORDER BY slot_time ASC
    """, (business_id, weekday))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return DEFAULT_AVAILABLE_TIMES

    return [str(row["slot_time"]) for row in rows if row.get("active")]


def get_service_record(service_name, business_id=1):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT service_name, duration_minutes, requires_deposit, deposit_amount
        FROM services
        WHERE business_id = %s
          AND LOWER(service_name) LIKE %s
          AND active = 1
        LIMIT 1
    """, (business_id, f"%{service_name.lower()}%"))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row


def get_service_duration_minutes(service_name, business_id=1):
    row = get_service_record(service_name, business_id)

    if not row:
        return 120

    return row.get("duration_minutes") or 120


def get_service_deposit_amount(service_name, business_id=1):
    row = get_service_record(service_name, business_id)

    if not row:
        return 150.00

    if not row.get("requires_deposit"):
        return 0.00

    return row.get("deposit_amount") or 0.00


def is_alaciado_service(service_name):
    normalized = (service_name or "").lower()
    return "alisado" in normalized or "alaciado" in normalized


def save_appointment(phone_number, customer_name, service_name, appointment_date, appointment_time, business_id=1, service_location='casa_mercedes'):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO appointments (
            business_id,
            customer_phone,
              service_location,
            customer_name,
            service_name,
            appointment_date,
            appointment_time,
            status,
            deposit_required,
            deposit_paid,
            notes
        )
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        business_id,
        phone_number,
          service_location,
        customer_name,
        service_name,
        appointment_date,
        appointment_time,
        "pending",
        get_service_deposit_amount(service_name, business_id),
        False,
        "Cita creada desde WhatsApp bot"
    ))

    conn.commit()
    cursor.close()
    conn.close()


def time_to_minutes(time_value):
    time_text = str(time_value)
    parts = time_text.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def is_slot_blocked(appointment_date, appointment_time, business_id=1):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM blocked_slots
        WHERE business_id = %s
          AND appointment_date = %s
          AND appointment_time = %s
        LIMIT 1
    """, (business_id, appointment_date, appointment_time))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None


def is_day_blocked(appointment_date, business_id=1):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date = %s
        LIMIT 1
    """, (business_id, appointment_date))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None


def is_time_slot_available(appointment_date, appointment_time, service_name=None, business_id=1):
    if is_alaciado_service(service_name) and str(appointment_time) not in ("10:00:00", "15:00:00"):
        return False

    if is_day_blocked(appointment_date, business_id):
        return False

    if is_slot_blocked(appointment_date, appointment_time, business_id):
        return False

    requested_duration = get_service_duration_minutes(service_name or "", business_id)
    requested_start = time_to_minutes(appointment_time)
    requested_end = requested_start + requested_duration

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            service_name,
            appointment_time
        FROM appointments
        WHERE business_id = %s
          AND appointment_date = %s
          AND status != 'canceled'
    """, (business_id, appointment_date))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    for row in rows:
        existing_service = row["service_name"]
        existing_time = row["appointment_time"]

        if (
            is_alaciado_service(existing_service)
            and str(existing_time) == "10:00:00"
            and requested_start >= time_to_minutes("12:00:00")
        ):
            return False

        existing_duration = get_service_duration_minutes(existing_service or "", business_id)
        existing_start = time_to_minutes(existing_time)
        existing_end = existing_start + existing_duration

        if ranges_overlap(requested_start, requested_end, existing_start, existing_end):
            return False

    return True


def format_time_for_user(time_value):
    time_text = str(time_value)

    if time_text == "10:00:00":
        return "10:00"
    if time_text == "12:00:00":
        return "12:00"
    if time_text == "15:00:00":
        return "15:00"

    return time_text[:5]


def get_available_times(appointment_date, service_name=None, business_id=1):
    available = []

    if is_day_blocked(appointment_date, business_id):
        return available

    now = datetime.now(ZoneInfo("America/Mexico_City"))
    today = now.date()
    current_minutes = now.hour * 60 + now.minute
    minimum_notice_minutes = 60

    for time_slot in get_business_time_slots(appointment_date, business_id):
        slot_minutes = time_to_minutes(time_slot)

        if str(appointment_date) == str(today):
            if slot_minutes <= current_minutes + minimum_notice_minutes:
                continue

        if is_time_slot_available(appointment_date, time_slot, service_name, business_id):
            available.append(time_slot)

    return available


def format_available_times_message(available_times):
    if not available_times:
        return None

    readable = [format_time_for_user(t) for t in available_times]

    if len(readable) == 1:
        return readable[0]

    if len(readable) == 2:
        return f"{readable[0]} o {readable[1]}"

    return f"{', '.join(readable[:-1])} o {readable[-1]}"
