from flask import redirect, render_template, request

from routes.dashboard import dashboard_bp
from services.business_service import get_business_by_slug
from services.customer_service import (
    get_business_customer,
    list_business_customer_appointments,
    list_business_customers_with_session_counts,
    update_business_customer,
)


def _get_wellness_business(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return None, ("Negocio no encontrado", 404)

    if business["business_type"] != "wellness":
        return None, ("Módulo no disponible para este negocio", 404)

    return business, None


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<slug>/clients"
)
def dashboard_wellness_clients(slug):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    customers = list_business_customers_with_session_counts(
        business["id"]
    )

    return render_template(
        "wellness_clients.html",
        business=business,
        customers=customers,
        active_page="clients",
        page_title="Clientes",
        page_subtitle="Personas registradas y su actividad",
    )


@dashboard_bp.get(
    "/whatsapp/dashboard/business/<slug>/clients/<int:customer_id>"
)
def dashboard_wellness_client_detail(slug, customer_id):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    customer = get_business_customer(
        customer_id,
        business["id"],
    )

    if not customer:
        return "Cliente no encontrado", 404

    appointments = list_business_customer_appointments(
        business["id"],
        customer["phone_number"],
    )

    total_sessions = len(appointments)

    completed_sessions = sum(
        1
        for appointment in appointments
        if appointment["status"] == "completed"
    )

    upcoming_sessions = sum(
        1
        for appointment in appointments
        if appointment["status"] in {"pending", "confirmed"}
    )

    return render_template(
        "wellness_client_detail.html",
        business=business,
        customer=customer,
        appointments=appointments,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        upcoming_sessions=upcoming_sessions,
        active_page="clients",
        page_title=(
            customer["preferred_name"]
            or customer["customer_name"]
            or "Cliente"
        ),
        page_subtitle="Ficha e historial del cliente",
    )


@dashboard_bp.route(
    "/whatsapp/dashboard/business/<slug>/clients/<int:customer_id>/edit",
    methods=["GET", "POST"],
)
def dashboard_wellness_client_edit(slug, customer_id):
    business, error_response = _get_wellness_business(slug)

    if error_response:
        return error_response

    customer = get_business_customer(
        customer_id,
        business["id"],
    )

    if not customer:
        return "Cliente no encontrado", 404

    error_message = None

    if request.method == "POST":
        try:
            update_business_customer(
                customer_id=customer_id,
                business_id=business["id"],
                customer_name=request.form.get("customer_name"),
                preferred_name=request.form.get("preferred_name"),
                phone_number=request.form.get("phone_number"),
                customer_notes=request.form.get("customer_notes"),
            )

            return redirect(
                f"/whatsapp/dashboard/business/{slug}"
                f"/clients/{customer_id}?customer_updated=1"
            )

        except ValueError as exc:
            error_message = str(exc)

            customer = {
                **customer,
                "customer_name": request.form.get("customer_name"),
                "preferred_name": request.form.get("preferred_name"),
                "phone_number": request.form.get("phone_number"),
                "customer_notes": request.form.get("customer_notes"),
            }

    return render_template(
        "wellness_client_edit.html",
        business=business,
        customer=customer,
        error_message=error_message,
        active_page="clients",
        page_title="Editar cliente",
        page_subtitle="Información administrativa del cliente",
    )
