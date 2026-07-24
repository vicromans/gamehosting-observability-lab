import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import redirect, render_template, request

from database.connection import get_db_connection
from routes.dashboard import dashboard_bp
from services.appointment_service import get_business_time_slots


@dashboard_bp.get("/whatsapp/dashboard/agenda")
def dashboard_agenda():
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()

    year = request.args.get("year", default=today.year, type=int)
    month = request.args.get("month", default=today.month, type=int)

    if month < 1:
        month = 12
        year -= 1

    if month > 12:
        month = 1
        year += 1

    first_day = datetime(year, month, 1).date()
    last_day_number = calendar.monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_number).date()

    previous_month = month - 1
    previous_year = year
    if previous_month < 1:
        previous_month = 12
        previous_year -= 1

    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.execute("""
        SELECT
            appointment_date,
            COUNT(*) AS total
        FROM appointments
        WHERE business_id = %s
          AND appointment_date BETWEEN %s AND %s
          AND status != 'canceled'
        GROUP BY appointment_date
    """, (1, first_day, last_day))
    appointment_days = cursor.fetchall()

    cursor.execute("""
        SELECT
            blocked_date,
            reason
        FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date BETWEEN %s AND %s
    """, (1, first_day, last_day))
    blocked_days = cursor.fetchall()

    cursor.execute("""
        SELECT
            appointment_date,
            COUNT(*) AS total
        FROM blocked_slots
        WHERE business_id = %s
          AND appointment_date BETWEEN %s AND %s
        GROUP BY appointment_date
    """, (1, first_day, last_day))
    partial_block_days = cursor.fetchall()

    cursor.close()
    conn.close()

    appointment_map = {str(row["appointment_date"]): row["total"] for row in appointment_days}
    blocked_map = {str(row["blocked_date"]): row["reason"] for row in blocked_days}
    partial_block_map = {str(row["appointment_date"]): row["total"] for row in partial_block_days}

    month_weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    calendar_weeks = []

    for week in month_weeks:
        calendar_week = []

        for day in week:
            date_key = str(day)

            is_current_month = day.month == month
            total_appointments = appointment_map.get(date_key, 0)
            is_blocked = date_key in blocked_map
            partial_blocks = partial_block_map.get(date_key, 0)

            status = "available"
            status_label = "Disponible"

            if is_blocked:
                status = "blocked"
                status_label = "Bloqueado"
            elif total_appointments >= 3:
                status = "full"
                status_label = "Lleno"
            elif partial_blocks > 0:
                status = "partial"
                status_label = "Parcial"
            elif total_appointments > 0:
                status = "appointments"
                status_label = "Con citas"

            calendar_week.append({
                "date": date_key,
                "day_number": day.day,
                "current_month": is_current_month,
                "total_appointments": total_appointments,
                "blocked": is_blocked,
                "blocked_reason": blocked_map.get(date_key),
                "partial_blocks": partial_blocks,
                "status": status,
                "status_label": status_label
            })

        calendar_weeks.append(calendar_week)

    total_appointments = sum(appointment_map.values())
    blocked_days_count = len(blocked_map)
    partial_blocks_count = sum(partial_block_map.values())

    total_slots = last_day_number * 3
    occupancy_percent = int((total_appointments / total_slots) * 100) if total_slots else 0

    month_stats = {
        "total_appointments": total_appointments,
        "blocked_days_count": blocked_days_count,
        "partial_blocks_count": partial_blocks_count,
        "occupancy_percent": occupancy_percent
    }

    month_name = first_day.strftime("%B %Y")

    return render_template(
        "agenda.html",
        business=business,
        active_page="agenda",
        page_title="Agenda",
        page_subtitle="Calendario mensual de citas y disponibilidad.",
        calendar_weeks=calendar_weeks,
        month_name=month_name,
        year=year,
        month=month,
        previous_year=previous_year,
        previous_month=previous_month,
        next_year=next_year,
        next_month=next_month,
        month_stats=month_stats,
        today_date=str(today)
    )


@dashboard_bp.get("/whatsapp/dashboard/agenda/week")
def dashboard_agenda_week():
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    selected_date_text = request.args.get("date")

    if selected_date_text:
        selected_date = datetime.strptime(selected_date_text, "%Y-%m-%d").date()
    else:
        selected_date = today

    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_end = week_start + timedelta(days=6)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.execute("""
        SELECT
            id,
            customer_name,
            customer_phone,
            service_location,
            service_name,
            appointment_date,
            appointment_time,
            status,
            deposit_required,
            deposit_paid,
            notes
        FROM appointments
        WHERE business_id = %s
          AND appointment_date BETWEEN %s AND %s
          AND status != 'canceled'
        ORDER BY appointment_date ASC, appointment_time ASC
    """, (1, week_start, week_end))
    appointments = cursor.fetchall()

    cursor.execute("""
        SELECT
            blocked_date,
            reason
        FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date BETWEEN %s AND %s
    """, (1, week_start, week_end))
    blocked_days = cursor.fetchall()

    cursor.execute("""
        SELECT
            appointment_date,
            appointment_time,
            reason
        FROM blocked_slots
        WHERE business_id = %s
          AND appointment_date BETWEEN %s AND %s
        ORDER BY appointment_date ASC, appointment_time ASC
    """, (1, week_start, week_end))
    blocked_slots = cursor.fetchall()

    cursor.close()
    conn.close()

    blocked_day_map = {
        str(row["blocked_date"]): row["reason"]
        for row in blocked_days
    }

    appointments_by_day = {}
    for row in appointments:
        date_key = str(row["appointment_date"])
        appointments_by_day.setdefault(date_key, []).append(row)

    blocked_slots_by_day = {}
    for row in blocked_slots:
        date_key = str(row["appointment_date"])
        blocked_slots_by_day.setdefault(date_key, []).append(row)

    week_days = []
    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for index in range(7):
        day = week_start + timedelta(days=index)
        date_key = str(day)

        week_days.append({
            "name": day_names[index],
            "date": date_key,
            "day_number": day.day,
            "blocked": date_key in blocked_day_map,
            "blocked_reason": blocked_day_map.get(date_key),
            "appointments": appointments_by_day.get(date_key, []),
            "blocked_slots": blocked_slots_by_day.get(date_key, [])
        })

    week_stats = {
        "total_appointments": len(appointments),
        "blocked_days_count": len(blocked_days),
        "partial_blocks_count": len(blocked_slots),
        "week_start": str(week_start),
        "week_end": str(week_end)
    }

    return render_template(
        "agenda_week.html",
        business=business,
        active_page="agenda",
        page_title="Agenda",
        page_subtitle=f"Semana del {week_start} al {week_end}.",
        week_days=week_days,
        week_stats=week_stats,
        selected_date=str(selected_date),
        previous_week=str(previous_week),
        next_week=str(next_week)
    )


@dashboard_bp.get("/whatsapp/dashboard/agenda/day/<appointment_date>")
def dashboard_agenda_day(appointment_date):
    selected_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
    previous_day = selected_date - timedelta(days=1)
    next_day = selected_date + timedelta(days=1)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM businesses WHERE id = %s", (1,))
    business = cursor.fetchone()

    cursor.execute("""
        SELECT
            id,
            customer_name,
            customer_phone,
            service_location,
            service_name,
            appointment_date,
            appointment_time,
            status,
            deposit_required,
            deposit_paid,
            notes
        FROM appointments
        WHERE business_id = %s
          AND appointment_date = %s
          AND status != 'canceled'
        ORDER BY appointment_time ASC
    """, (1, appointment_date))
    appointments = cursor.fetchall()

    cursor.execute("""
        SELECT id, reason
        FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date = %s
        LIMIT 1
    """, (1, appointment_date))
    day_block = cursor.fetchone()

    cursor.execute("""
        SELECT
            appointment_time,
            reason
        FROM blocked_slots
        WHERE business_id = %s
          AND appointment_date = %s
        ORDER BY appointment_time ASC
    """, (1, appointment_date))
    blocked_slots = cursor.fetchall()

    cursor.close()
    conn.close()

    appointments_by_time = {
        str(row["appointment_time"]): row
        for row in appointments
    }

    blocked_slots_by_time = {
        str(row["appointment_time"]): row
        for row in blocked_slots
    }

    timeline_slots = []

    for slot_time in get_business_time_slots(appointment_date, 1):
        appointment = appointments_by_time.get(str(slot_time))
        blocked_slot = blocked_slots_by_time.get(str(slot_time))

        status = "available"
        if day_block:
            status = "day_blocked"
        elif blocked_slot:
            status = "blocked"
        elif appointment:
            status = "appointment"

        timeline_slots.append({
            "time": str(slot_time),
            "status": status,
            "appointment": appointment,
            "blocked_slot": blocked_slot
        })

    return render_template(
        "agenda_day.html",
        business=business,
        active_page="agenda",
        page_title="Agenda",
        page_subtitle=f"Citas del día {appointment_date}",
        appointment_date=appointment_date,
        previous_day=str(previous_day),
        next_day=str(next_day),
        appointments=appointments,
        day_block=day_block,
        timeline_slots=timeline_slots
    )


@dashboard_bp.post("/whatsapp/dashboard/agenda/day/<appointment_date>/block")
def dashboard_block_day(appointment_date):
    reason = request.form.get("reason") or "Bloqueado desde dashboard"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date = %s
        LIMIT 1
    """, (1, appointment_date))

    existing = cursor.fetchone()

    if not existing:
        cursor.execute("""
            INSERT INTO availability_exceptions
            (business_id, blocked_date, reason)
            VALUES (%s, %s, %s)
        """, (1, appointment_date, reason))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(f"/whatsapp/dashboard/agenda/day/{appointment_date}")


@dashboard_bp.post("/whatsapp/dashboard/agenda/day/<appointment_date>/unblock")
def dashboard_unblock_day(appointment_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM availability_exceptions
        WHERE business_id = %s
          AND blocked_date = %s
    """, (1, appointment_date))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(f"/whatsapp/dashboard/agenda/day/{appointment_date}")


@dashboard_bp.route("/dashboard/appointments/<int:appointment_id>/<action>", methods=["POST"])
@dashboard_bp.route("/whatsapp/dashboard/appointments/<int:appointment_id>/<action>", methods=["POST"])
def update_appointment_status(appointment_id, action):
    valid_actions = {
        "confirm": "confirmed",
        "cancel": "cancelled",
        "complete": "completed"
    }

    if action not in valid_actions:
        return "Acción inválida", 400

    new_status = valid_actions[action]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = %s
        WHERE id = %s AND business_id = 1
    """, (new_status, appointment_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/whatsapp/dashboard")
