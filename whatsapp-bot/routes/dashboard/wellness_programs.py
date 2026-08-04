from decimal import Decimal, InvalidOperation

from flask import redirect, render_template, request

from routes.dashboard import dashboard_bp
from services.business_service import get_business_by_slug
from services.customer_service import list_business_customers_with_session_counts
from services.wellness.program_service import (
    VALID_DELIVERY_MODES,
    VALID_PROGRAM_TYPES,
    add_program_session,
    create_program,
    create_program_registration,
    delete_program_registration,
    delete_program_session,
    get_program,
    get_program_registration,
    list_program_registrations,
    list_programs,
    update_program,
    update_program_registration,
    update_program_session,
)


def _get_wellness_business(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return None, ("Negocio no encontrado", 404)

    if business["business_type"] != "wellness":
        return None, ("Módulo no disponible para este negocio", 404)

    return business, None


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/events",
    methods=["GET", "POST"],
)
def dashboard_wellness_events(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    error_message = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        program_type = (request.form.get("program_type") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        delivery_mode = (request.form.get("delivery_mode") or "").strip()

        location_name = (request.form.get("location_name") or "").strip() or None
        online_platform = (
            request.form.get("online_platform") or ""
        ).strip() or None

        is_free = request.form.get("is_free") == "1"

        raw_price = (request.form.get("price") or "").strip()
        price = None

        if raw_price and not is_free:
            try:
                price = Decimal(raw_price)
            except InvalidOperation:
                error_message = "El precio no es válido."

        raw_capacity = (request.form.get("capacity") or "").strip()
        capacity = None

        if raw_capacity:
            try:
                capacity = int(raw_capacity)
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                error_message = "El cupo debe ser un número mayor que cero."

        if not error_message:
            try:
                create_program(
                    business_id=business["id"],
                    title=title,
                    program_type=program_type,
                    description=description,
                    delivery_mode=delivery_mode,
                    location_name=location_name,
                    online_platform=online_platform,
                    is_free=is_free,
                    price=price,
                    currency="MXN",
                    capacity=capacity,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}/events?created=1"
            )

    programs = list_programs(business["id"])
    created = request.args.get("created") == "1"

    return render_template(
        "wellness_events.html",
        business=business,
        programs=programs,
        created=created,
        error_message=error_message,
        program_types=sorted(VALID_PROGRAM_TYPES),
        delivery_modes=sorted(VALID_DELIVERY_MODES),
        active_page="events",
        page_title="Eventos y Talleres",
        page_subtitle="Programas, talleres, retos, retiros y masterclasses",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>",
    methods=["GET", "POST"],
)
def dashboard_wellness_program_detail(slug, program_id):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    error_message = None

    if request.method == "POST":
        session_date = (request.form.get("session_date") or "").strip()
        start_time = (request.form.get("start_time") or "").strip() or None
        end_time = (request.form.get("end_time") or "").strip() or None
        session_title = (
            request.form.get("session_title") or ""
        ).strip() or None

        if not session_date:
            error_message = "La fecha es obligatoria."

        if (
            not error_message
            and start_time
            and end_time
            and end_time <= start_time
        ):
            error_message = (
                "La hora de término debe ser posterior "
                "a la hora de inicio."
            )

        if not error_message:
            add_program_session(
                program_id=program["id"],
                session_date=session_date,
                start_time=start_time,
                end_time=end_time,
                session_title=session_title,
            )

            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/events/{program_id}?session_added=1"
            )

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    session_added = request.args.get("session_added") == "1"

    registration_error = request.args.get("registration_error")

    if registration_error == "duplicado":
        error_message = (
            "Este cliente ya está inscrito en esta actividad."
        )
    elif registration_error == "cliente":
        error_message = "Selecciona un cliente válido."
    elif registration_error == "monto":
        error_message = "El monto pagado no es válido."
    elif registration_error == "general":
        error_message = (
            "No fue posible registrar al participante."
        )

    registrations = list_program_registrations(
        program["id"],
        business["id"],
    )

    customers = list_business_customers_with_session_counts(
        business["id"]
    )

    return render_template(
        "wellness_program_detail.html",
        business=business,
        program=program,
        registrations=registrations,
        customers=customers,
        session_added=session_added,
        registration_added=(
            request.args.get("registration_added") == "1"
        ),
        error_message=error_message,
        active_page="events",
        page_title=program["title"],
        page_subtitle="Administración de actividad",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_program_edit(slug, program_id):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    error_message = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        program_type = (request.form.get("program_type") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        delivery_mode = (request.form.get("delivery_mode") or "").strip()
        location_name = (
            request.form.get("location_name") or ""
        ).strip() or None
        online_platform = (
            request.form.get("online_platform") or ""
        ).strip() or None

        is_free = request.form.get("is_free") == "1"

        raw_price = (request.form.get("price") or "").strip()
        price = None

        if raw_price and not is_free:
            try:
                price = Decimal(raw_price)
            except InvalidOperation:
                error_message = "El precio no es válido."

        raw_capacity = (request.form.get("capacity") or "").strip()
        capacity = None

        if raw_capacity:
            try:
                capacity = int(raw_capacity)
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                error_message = "El cupo debe ser un número mayor que cero."

        if not error_message:
            try:
                update_program(
                    program_id=program["id"],
                    business_id=business["id"],
                    title=title,
                    program_type=program_type,
                    description=description,
                    delivery_mode=delivery_mode,
                    location_name=location_name,
                    online_platform=online_platform,
                    is_free=is_free,
                    price=price,
                    currency="MXN",
                    capacity=capacity,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/events/{program_id}?updated=1"
            )

    return render_template(
        "wellness_program_edit.html",
        business=business,
        program=program,
        error_message=error_message,
        active_page="events",
        page_title="Editar actividad",
        page_subtitle=program["title"],
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>"
    "/sessions/<int:session_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_session_edit(
    slug,
    program_id,
    session_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    session = next(
        (
            item
            for item in program.get("sessions", [])
            if int(item["id"]) == session_id
        ),
        None,
    )

    if not session:
        return "Fecha no encontrada", 404

    def _time_input_value(value):
        if value is None:
            return ""

        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return f"{hours:02d}:{minutes:02d}"

    session["start_time_input"] = _time_input_value(
        session.get("start_time")
    )
    session["end_time_input"] = _time_input_value(
        session.get("end_time")
    )

    error_message = None

    if request.method == "POST":
        session_date = (
            request.form.get("session_date") or ""
        ).strip()

        start_time = (
            request.form.get("start_time") or ""
        ).strip() or None

        end_time = (
            request.form.get("end_time") or ""
        ).strip() or None

        session_title = (
            request.form.get("session_title") or ""
        ).strip() or None

        if not session_date:
            error_message = "La fecha es obligatoria."

        if (
            not error_message
            and start_time
            and end_time
            and end_time <= start_time
        ):
            error_message = (
                "La hora de término debe ser posterior "
                "a la hora de inicio."
            )

        if not error_message:
            update_program_session(
                session_id=session_id,
                program_id=program_id,
                session_date=session_date,
                start_time=start_time,
                end_time=end_time,
                session_title=session_title,
            )

            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/events/{program_id}?session_updated=1"
            )

    return render_template(
        "wellness_session_edit.html",
        business=business,
        program=program,
        session=session,
        error_message=error_message,
        active_page="events",
        page_title="Editar fecha",
        page_subtitle=program["title"],
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>"
    "/sessions/<int:session_id>/delete"
)
def dashboard_wellness_session_delete(
    slug,
    program_id,
    session_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    valid_session_ids = {
        int(item["id"])
        for item in program.get("sessions", [])
    }

    if session_id not in valid_session_ids:
        return "Fecha no encontrada", 404

    delete_program_session(
        session_id=session_id,
        program_id=program_id,
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/events/{program_id}?session_deleted=1"
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>/registrations"
)
def dashboard_wellness_program_registration_add(
    slug,
    program_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    raw_customer_id = (
        request.form.get("customer_id") or ""
    ).strip()

    payment_status = (
        request.form.get("payment_status") or "pending"
    ).strip()

    raw_amount = (
        request.form.get("amount_paid") or ""
    ).strip()

    notes = (
        request.form.get("registration_notes") or ""
    ).strip() or None

    try:
        customer_id = int(raw_customer_id)
    except (TypeError, ValueError):
        return redirect(
            f"/whatsapp/dashboard/business/{slug}"
            f"/events/{program_id}?registration_error=cliente"
        )

    amount_paid = None

    if raw_amount:
        try:
            amount_paid = Decimal(raw_amount)
        except InvalidOperation:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/events/{program_id}?registration_error=monto"
            )

    try:
        create_program_registration(
            program_id=program["id"],
            business_id=business["id"],
            customer_id=customer_id,
            registration_status="registered",
            payment_status=payment_status,
            amount_paid=amount_paid,
            notes=notes,
        )
    except ValueError as exc:
        error_text = str(exc)

        if "ya está inscrito" in error_text:
            error_code = "duplicado"
        else:
            error_code = "general"

        return redirect(
            f"/whatsapp/dashboard/business/{slug}"
            f"/events/{program_id}?registration_error={error_code}"
        )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/events/{program_id}?registration_added=1"
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>"
    "/registrations/<int:registration_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_program_registration_edit(
    slug,
    program_id,
    registration_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    registration = get_program_registration(
        registration_id=registration_id,
        program_id=program_id,
        business_id=business["id"],
    )

    if not registration:
        return "Inscripción no encontrada", 404

    error_message = None

    if request.method == "POST":
        registration_status = (
            request.form.get("registration_status") or ""
        ).strip()

        payment_status = (
            request.form.get("payment_status") or ""
        ).strip()

        raw_amount = (
            request.form.get("amount_paid") or ""
        ).strip()

        notes = (
            request.form.get("notes") or ""
        ).strip() or None

        amount_paid = None

        if raw_amount:
            try:
                amount_paid = Decimal(raw_amount)
            except InvalidOperation:
                error_message = "El monto pagado no es válido."

        if not error_message:
            try:
                update_program_registration(
                    registration_id=registration_id,
                    program_id=program_id,
                    business_id=business["id"],
                    registration_status=registration_status,
                    payment_status=payment_status,
                    amount_paid=amount_paid,
                    notes=notes,
                )
            except ValueError as exc:
                error_message = str(exc)

        if not error_message:
            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/events/{program_id}?registration_updated=1"
            )

        registration = {
            **registration,
            "registration_status": registration_status,
            "payment_status": payment_status,
            "amount_paid": amount_paid,
            "notes": notes,
        }

    return render_template(
        "wellness_program_registration_edit.html",
        business=business,
        program=program,
        registration=registration,
        error_message=error_message,
        active_page="events",
        page_title="Editar participante",
        page_subtitle=program["title"],
    )


@dashboard_bp.post(
    "/whatsapp/dashboard/business/<slug>/events/<int:program_id>"
    "/registrations/<int:registration_id>/delete"
)
def dashboard_wellness_program_registration_delete(
    slug,
    program_id,
    registration_id,
):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    program = get_program(
        program_id,
        business_id=business["id"],
    )

    if not program:
        return "Actividad no encontrada", 404

    registration = get_program_registration(
        registration_id=registration_id,
        program_id=program_id,
        business_id=business["id"],
    )

    if not registration:
        return "Inscripción no encontrada", 404

    delete_program_registration(
        registration_id=registration_id,
        program_id=program_id,
        business_id=business["id"],
    )

    return redirect(
        f"/whatsapp/dashboard/business/{slug}"
        f"/events/{program_id}?registration_deleted=1"
    )
