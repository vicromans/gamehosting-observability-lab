from decimal import Decimal, InvalidOperation

from flask import redirect, render_template, request

from routes.dashboard import dashboard_bp
from services.business_service import get_business_by_slug
from services.wellness.session_service import (
    VALID_DELIVERY_MODES,
    add_availability_range,
    create_schedule_block,
    create_session_type,
    create_wellness_appointment,
    delete_schedule_block,
    delete_availability_range,
    delete_session_type,
    get_availability_range,
    get_schedule_block,
    get_session_type,
    get_wellness_appointment,
    list_availability,
    list_schedule_blocks,
    list_session_types,
    list_wellness_appointments,
    update_availability_range,
    update_schedule_block,
    update_session_type,
    update_wellness_appointment,
)


WEEKDAY_LABELS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _get_wellness_business(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return None, ("Negocio no encontrado", 404)

    if business["business_type"] != "wellness":
        return None, ("Módulo no disponible para este negocio", 404)

    return business, None


def _time_to_hhmm(value):
    if value is None:
        return ""

    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return f"{hours:02d}:{minutes:02d}"


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/settings",
    methods=["GET", "POST"],
)
def dashboard_wellness_sessions_settings(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    error_message = None

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        if action == "create_session_type":
            name = (request.form.get("name") or "").strip()
            description = (
                request.form.get("description") or ""
            ).strip() or None

            raw_duration = (
                request.form.get("duration_minutes") or ""
            ).strip()

            raw_price = (request.form.get("price") or "").strip()

            delivery_mode = (
                request.form.get("delivery_mode") or ""
            ).strip()

            price = None

            if raw_price:
                try:
                    price = Decimal(raw_price)
                except InvalidOperation:
                    error_message = "El precio no es válido."

            if not error_message:
                try:
                    create_session_type(
                        business_id=business["id"],
                        name=name,
                        description=description,
                        duration_minutes=raw_duration,
                        price=price,
                        currency="MXN",
                        delivery_mode=delivery_mode,
                    )
                except ValueError as exc:
                    error_message = str(exc)

            if not error_message:
                return redirect(
                    f"/whatsapp/dashboard/business/{slug}"
                    f"/sessions/settings?session_type_created=1"
                )

        elif action == "add_availability":
            weekday = (request.form.get("weekday") or "").strip()
            start_time = (request.form.get("start_time") or "").strip()
            end_time = (request.form.get("end_time") or "").strip()

            try:
                add_availability_range(
                    business_id=business["id"],
                    weekday=weekday,
                    start_time=start_time,
                    end_time=end_time,
                )
            except ValueError as exc:
                error_message = str(exc)

            if not error_message:
                return redirect(
                    f"/whatsapp/dashboard/business/{slug}"
                    f"/sessions/settings?availability_created=1"
                )

        else:
            error_message = "Acción no válida."

    session_types = list_session_types(
        business["id"],
        include_inactive=False,
    )

    availability = list_availability(business["id"])

    for item in availability:
        item["weekday_label"] = WEEKDAY_LABELS.get(
            int(item["weekday"]),
            "Día",
        )
        item["start_time_label"] = _time_to_hhmm(
            item.get("start_time")
        )
        item["end_time_label"] = _time_to_hhmm(
            item.get("end_time")
        )

    return render_template(
        "wellness_sessions.html",
        business=business,
        session_types=session_types,
        availability=availability,
        error_message=error_message,
        session_type_created=(
            request.args.get("session_type_created") == "1"
        ),
        availability_created=(
            request.args.get("availability_created") == "1"
        ),
        active_page="sessions",
        page_title="Configuración de sesiones",
        page_subtitle=(
            "Tipos de sesión y disponibilidad semanal"
        ),
    )


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<slug>/sessions"
)
def dashboard_wellness_sessions(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    appointments = list_wellness_appointments(
        business_id=business["id"],
    )

    schedule_blocks = list_schedule_blocks(
        business_id=business["id"],
    )

    for block in schedule_blocks:
        block["start_time_label"] = _time_to_hhmm(
            block.get("start_time")
        )
        block["end_time_label"] = _time_to_hhmm(
            block.get("end_time")
        )

    for appointment in appointments:
        start_value = appointment.get("appointment_time")
        duration = appointment.get("duration_minutes") or 0

        if start_value is not None:
            start_seconds = int(start_value.total_seconds())
            end_seconds = start_seconds + (duration * 60)

            start_hours = start_seconds // 3600
            start_minutes = (start_seconds % 3600) // 60

            end_hours = end_seconds // 3600
            end_minutes = (end_seconds % 3600) // 60

            appointment["start_time_label"] = (
                f"{start_hours:02d}:{start_minutes:02d}"
            )
            appointment["end_time_label"] = (
                f"{end_hours:02d}:{end_minutes:02d}"
            )
        else:
            appointment["start_time_label"] = ""
            appointment["end_time_label"] = ""

    return render_template(
        "wellness_sessions_agenda.html",
        business=business,
        appointments=appointments,
        schedule_blocks=schedule_blocks,
        active_page="sessions",
        page_title="Sesiones",
        page_subtitle="Agenda de sesiones individuales",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/types/<int:session_type_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_session_type_edit(
    slug,
    session_type_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    session_type = get_session_type(
        session_type_id,
        business["id"],
    )

    if not session_type:
        return "Tipo de sesión no encontrado", 404

    error_message = None

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()

        description = (
            request.form.get("description") or ""
        ).strip() or None

        raw_duration = (
            request.form.get("duration_minutes") or ""
        ).strip()

        raw_price = (
            request.form.get("price") or ""
        ).strip()

        delivery_mode = (
            request.form.get("delivery_mode") or ""
        ).strip()

        price = None

        if raw_price:
            try:
                price = Decimal(raw_price)
            except InvalidOperation:
                error_message = "El precio no es válido."

        if not error_message:
            try:
                update_session_type(
                    session_type_id=session_type_id,
                    business_id=business["id"],
                    name=name,
                    duration_minutes=raw_duration,
                    description=description,
                    price=price,
                    currency="MXN",
                    delivery_mode=delivery_mode,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions/settings?session_type_updated=1"
            )

    return render_template(
        "wellness_session_type_edit.html",
        business=business,
        session_type=session_type,
        error_message=error_message,
        active_page="sessions",
        page_title="Editar tipo de sesión",
        page_subtitle=session_type["name"],
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/availability/<int:availability_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_availability_edit(
    slug,
    availability_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    availability = get_availability_range(
        availability_id,
        business["id"],
    )

    if not availability:
        return "Horario no encontrado", 404

    availability["start_time_input"] = _time_to_hhmm(
        availability.get("start_time")
    )
    availability["end_time_input"] = _time_to_hhmm(
        availability.get("end_time")
    )

    error_message = None

    if request.method == "POST":
        weekday = (request.form.get("weekday") or "").strip()
        start_time = (request.form.get("start_time") or "").strip()
        end_time = (request.form.get("end_time") or "").strip()

        try:
            update_availability_range(
                availability_id=availability_id,
                business_id=business["id"],
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
            )
        except ValueError as exc:
            error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions/settings?availability_updated=1"
            )

    return render_template(
        "wellness_availability_edit.html",
        business=business,
        availability=availability,
        weekday_labels=WEEKDAY_LABELS,
        error_message=error_message,
        active_page="sessions",
        page_title="Editar disponibilidad",
        page_subtitle=(
            WEEKDAY_LABELS.get(
                int(availability["weekday"]),
                "Horario",
            )
        ),
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/sessions/availability/<int:availability_id>/delete"
)
def dashboard_wellness_availability_delete(
    slug,
    availability_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    availability = get_availability_range(
        availability_id,
        business["id"],
    )

    if not availability:
        return "Horario no encontrado", 404

    delete_availability_range(
        availability_id,
        business["id"],
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/sessions/settings?availability_deleted=1"
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/sessions/types/<int:session_type_id>/delete"
)
def dashboard_wellness_session_type_delete(
    slug,
    session_type_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    session_type = get_session_type(
        session_type_id,
        business["id"],
    )

    if not session_type:
        return "Tipo de sesión no encontrado", 404

    delete_session_type(
        session_type_id,
        business["id"],
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/sessions/settings?session_type_deleted=1"
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/new",
    methods=["GET", "POST"],
)
def dashboard_wellness_session_new(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    session_types = list_session_types(
        business["id"],
    )

    error_message = None

    if request.method == "POST":
        raw_session_type_id = (
            request.form.get("session_type_id") or ""
        ).strip()

        customer_name = (
            request.form.get("customer_name") or ""
        ).strip()

        customer_phone = (
            request.form.get("customer_phone") or ""
        ).strip()

        appointment_date = (
            request.form.get("appointment_date") or ""
        ).strip()

        appointment_time = (
            request.form.get("appointment_time") or ""
        ).strip()

        status = (
            request.form.get("status") or "pending"
        ).strip()

        notes = (
            request.form.get("notes") or ""
        ).strip() or None

        try:
            session_type_id = int(raw_session_type_id)
        except (TypeError, ValueError):
            session_type_id = None
            error_message = "Selecciona un tipo de sesión."

        if not error_message:
            try:
                create_wellness_appointment(
                    business_id=business["id"],
                    session_type_id=session_type_id,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status=status,
                    notes=notes,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions?appointment_created=1"
            )

    return render_template(
        "wellness_session_new.html",
        business=business,
        session_types=session_types,
        error_message=error_message,
        active_page="sessions",
        page_title="Nueva sesión",
        page_subtitle="Agendar sesión individual",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/<int:appointment_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_appointment_edit(
    slug,
    appointment_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    appointment = get_wellness_appointment(
        appointment_id,
        business["id"],
    )

    if not appointment:
        return "Sesión no encontrada", 404

    session_types = list_session_types(
        business["id"],
    )

    appointment["appointment_time_input"] = _time_to_hhmm(
        appointment.get("appointment_time")
    )

    error_message = None

    if request.method == "POST":
        raw_session_type_id = (
            request.form.get("session_type_id") or ""
        ).strip()

        customer_name = (
            request.form.get("customer_name") or ""
        ).strip()

        customer_phone = (
            request.form.get("customer_phone") or ""
        ).strip()

        appointment_date = (
            request.form.get("appointment_date") or ""
        ).strip()

        appointment_time = (
            request.form.get("appointment_time") or ""
        ).strip()

        status = (
            request.form.get("status") or "pending"
        ).strip()

        notes = (
            request.form.get("notes") or ""
        ).strip() or None

        try:
            session_type_id = int(raw_session_type_id)
        except (TypeError, ValueError):
            session_type_id = None
            error_message = "Selecciona un tipo de sesión."

        if not error_message:
            try:
                update_wellness_appointment(
                    appointment_id=appointment_id,
                    business_id=business["id"],
                    session_type_id=session_type_id,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status=status,
                    notes=notes,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions?appointment_updated=1"
            )

    return render_template(
        "wellness_session_edit.html",
        business=business,
        appointment=appointment,
        session_types=session_types,
        error_message=error_message,
        active_page="sessions",
        page_title="Editar sesión",
        page_subtitle=appointment["customer_name"],
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/blocks/new",
    methods=["GET", "POST"],
)
def dashboard_wellness_schedule_block_new(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    error_message = None

    if request.method == "POST":
        blocked_date = (
            request.form.get("blocked_date") or ""
        ).strip()

        block_type = (
            request.form.get("block_type") or "full_day"
        ).strip()

        reason = (
            request.form.get("reason") or ""
        ).strip() or None

        start_time = None
        end_time = None

        if block_type == "partial":
            start_time = (
                request.form.get("start_time") or ""
            ).strip()

            end_time = (
                request.form.get("end_time") or ""
            ).strip()

        try:
            create_schedule_block(
                business_id=business["id"],
                blocked_date=blocked_date,
                start_time=start_time,
                end_time=end_time,
                reason=reason,
            )
        except ValueError as exc:
            error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions?block_created=1"
            )

    return render_template(
        "wellness_schedule_block_new.html",
        business=business,
        error_message=error_message,
        active_page="sessions",
        page_title="Bloquear agenda",
        page_subtitle="Reservar tiempo personal",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/sessions/blocks/<int:block_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_schedule_block_edit(
    slug,
    block_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    block = get_schedule_block(
        block_id,
        business["id"],
    )

    if not block:
        return "Bloqueo no encontrado", 404

    block["start_time_input"] = _time_to_hhmm(
        block.get("start_time")
    )
    block["end_time_input"] = _time_to_hhmm(
        block.get("end_time")
    )

    error_message = None

    if request.method == "POST":
        blocked_date = (
            request.form.get("blocked_date") or ""
        ).strip()

        block_type = (
            request.form.get("block_type") or "full_day"
        ).strip()

        reason = (
            request.form.get("reason") or ""
        ).strip() or None

        start_time = None
        end_time = None

        if block_type == "partial":
            start_time = (
                request.form.get("start_time") or ""
            ).strip()

            end_time = (
                request.form.get("end_time") or ""
            ).strip()

        try:
            update_schedule_block(
                block_id=block_id,
                business_id=business["id"],
                blocked_date=blocked_date,
                start_time=start_time,
                end_time=end_time,
                reason=reason,
            )
        except ValueError as exc:
            error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/sessions?block_updated=1"
            )

    return render_template(
        "wellness_schedule_block_edit.html",
        business=business,
        block=block,
        error_message=error_message,
        active_page="sessions",
        page_title="Editar bloqueo",
        page_subtitle="Modificar tiempo reservado",
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/sessions/blocks/<int:block_id>/delete"
)
def dashboard_wellness_schedule_block_delete(
    slug,
    block_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    block = get_schedule_block(
        block_id,
        business["id"],
    )

    if not block:
        return "Bloqueo no encontrado", 404

    delete_schedule_block(
        block_id,
        business["id"],
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/sessions?block_deleted=1"
    )
