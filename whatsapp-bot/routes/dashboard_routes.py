from flask import jsonify, render_template, request, redirect, send_from_directory

from database.connection import get_db_connection
from services.whatsapp_service import (
    send_whatsapp_message,
    send_whatsapp_template_message,
)
from meta_errors import translate_meta_error
from services.business_service import get_business_by_slug, get_default_business
import os

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_MEDIA_DIR = os.getenv(
    "WHATSAPP_MEDIA_DIR",
    "/app/static/uploads/whatsapp",
)
from datetime import datetime
from zoneinfo import ZoneInfo

from routes.dashboard import dashboard_bp


@dashboard_bp.get("/health")
@dashboard_bp.get("/whatsapp/health")
def health():
    return jsonify({"status": "ok", "service": "whatsapp-bot"})


@dashboard_bp.route("/whatsapp/dashboard/inbox")
def dashboard_inbox():
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.customer_name,
                c.phone_number,
                c.human_required,
                (
                    SELECT incoming_message
                    FROM whatsapp_messages wm
                    WHERE wm.phone_number = c.phone_number
                    ORDER BY wm.created_at DESC
                    LIMIT 1
                ) AS last_message,
                (
                    SELECT created_at
                    FROM whatsapp_messages wm
                    WHERE wm.phone_number = c.phone_number
                    ORDER BY wm.created_at DESC
                    LIMIT 1
                ) AS last_message_at
            FROM customers c
            WHERE c.human_required = 1
            ORDER BY last_message_at DESC
        """)

        customers = cursor.fetchall()

        cursor.execute("SELECT * FROM businesses WHERE id = 1")
        business = cursor.fetchone()

        return render_template(
            "inbox.html",
            business=business,
            customers=customers,
            active_page="inbox"
        )

    finally:
        conn.close()


@dashboard_bp.get("/whatsapp/dashboard/business/<slug>")
def dashboard_business_home(slug):
    business = get_business_by_slug(slug)

    if not business or not business["active"]:
        return "Negocio no encontrado", 404

    return render_template(
        "business_home.html",
        business=business,
        page_title=business["business_name"],
        page_subtitle="Panel de administración de VeldrikLabs",
        active_page="dashboard",
    )


@dashboard_bp.get("/dashboard")
@dashboard_bp.get("/whatsapp/dashboard")
def dashboard():
    local_today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM businesses WHERE id = 1")
            business = cursor.fetchone()

            cursor.execute("""
                SELECT id, phone_number, customer_name, allergy_notes, accepted_policies, human_required, last_contact
                FROM customers
                WHERE business_id = 1
                ORDER BY human_required DESC, last_contact DESC
                LIMIT 10
            """)
            customers = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    phone_number,
                    customer_name,
                    last_contact
                FROM customers
                WHERE business_id = 1
                  AND human_required = 1
                ORDER BY last_contact DESC
            """)
            human_queue = cursor.fetchall()

            cursor.execute("""
                SELECT id, service_name, price, duration_minutes, requires_deposit, deposit_amount, warranty_days
                FROM services
                WHERE business_id = 1 AND active = 1
                ORDER BY id ASC
            """)
            services = cursor.fetchall()

            cursor.execute("""
                SELECT id, phone_number, incoming_message, detected_intent, created_at
                FROM whatsapp_messages
                WHERE business_id = 1
                ORDER BY created_at DESC
                LIMIT 10
            """)
            messages = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    customer_name,
                    customer_phone,
                    service_name,
                    appointment_date,
                    appointment_time,
                    status,
                    deposit_required,
                    deposit_paid,
                    created_at
                FROM appointments
                WHERE business_id = 1
                  AND appointment_date >= %s
                ORDER BY appointment_date ASC, appointment_time ASC
                LIMIT 20
            """, (local_today,))
            appointments = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    customer_name,
                    customer_phone,
                    service_name,
                    appointment_date,
                    appointment_time,
                    status,
                    deposit_required,
                    deposit_paid
                FROM appointments
                WHERE business_id = 1
                  AND appointment_date = %s
                ORDER BY appointment_time ASC
            """, (local_today,))
            today_appointments = cursor.fetchall()

        return render_template(
            "dashboard.html",
            business=business,
            customers=customers,
            human_queue=human_queue,
            services=services,
            messages=messages,
            appointments=appointments,
            today_appointments=today_appointments,
            local_today=local_today,
            active_page="dashboard"
        )

    finally:
        connection.close()


@dashboard_bp.get("/whatsapp/dashboard/clients")
def dashboard_clients():
    connection = get_db_connection()

    try:
        business = get_default_business()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    phone_number,
                    customer_name,
                    allergy_notes,
                    accepted_policies,
                    human_required,
                    last_contact
                FROM customers
                WHERE business_id = %s
                ORDER BY last_contact DESC
            """, (business["id"],))
            customers = cursor.fetchall()

        return render_template(
            "clients.html",
            business=business,
            customers=customers,
            active_page="clients"
        )

    finally:
        connection.close()


@dashboard_bp.route(
    "/whatsapp/dashboard/customers/<int:customer_id>/resolved",
    methods=["POST"]
)
def resolve_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE customers
        SET human_required = 0
        WHERE id = %s
    """, (customer_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/whatsapp/dashboard")


@dashboard_bp.route("/whatsapp/dashboard/customer/<int:customer_id>", methods=["GET", "POST"])
def customer_conversation(customer_id):
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        if request.method == "POST":
            manual_reply = request.form.get("reply", "").strip()

            cursor.execute("""
                SELECT phone_number
                FROM customers
                WHERE id = %s
                LIMIT 1
            """, (customer_id,))

            customer_phone_row = cursor.fetchone()

            if manual_reply and customer_phone_row:
                phone_number = customer_phone_row["phone_number"]

                cursor.execute("""
                    INSERT INTO whatsapp_messages
                        (business_id, phone_number, incoming_message, bot_reply, detected_intent)
                    VALUES
                        (1, %s, NULL, %s, 'human_reply')
                """, (phone_number, manual_reply))

                send_whatsapp_message(
                    phone_number,
                    manual_reply,
                    WHATSAPP_PHONE_NUMBER_ID,
                    WHATSAPP_TOKEN
                )

                conn.commit()

            return redirect(f"/whatsapp/dashboard/customer/{customer_id}#bottom")

        cursor.execute("""
            SELECT
                id,
                customer_name,
                phone_number
            FROM customers
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        cursor.execute("""
            SELECT
                wm.id,
                wm.incoming_message,
                wm.bot_reply,
                wm.detected_intent,
                wm.created_at,
                media.media_type,
                media.mime_type,
                media.local_path
            FROM whatsapp_messages wm
            LEFT JOIN whatsapp_media media
                ON media.message_id = wm.id
            WHERE wm.business_id = 1
              AND wm.phone_number = %s
            ORDER BY wm.created_at ASC
        """, (customer["phone_number"],))

        messages = cursor.fetchall()

        cursor.execute("SELECT * FROM businesses WHERE id = 1")
        business = cursor.fetchone()

        return render_template(
            "customer_conversation.html",
            business=business,
            customer=customer,
            messages=messages,
            active_page="clients"
        )

    finally:
        conn.close()


@dashboard_bp.route("/whatsapp/dashboard/customer/<int:customer_id>/send-template", methods=["POST"])
def send_customer_template(customer_id):
    template_name = request.form.get("template_name", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    topic = request.form.get("topic", "").strip()

    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT phone_number
            FROM customers
            WHERE id = %s
            LIMIT 1
        """, (customer_id,))

        customer = cursor.fetchone()

        if not customer:
            return redirect("/whatsapp/dashboard/clients")

        phone_number = customer["phone_number"]

        response = send_whatsapp_template_message(
            phone_number,
            template_name,
            customer_name,
            topic,
            WHATSAPP_PHONE_NUMBER_ID,
            WHATSAPP_TOKEN
        )

        if response.status_code in (200, 201):
            message_log = f"[Plantilla enviada] {template_name} para {customer_name}: {topic}"
            intent = "template_sent"
        else:
            friendly_error = translate_meta_error(response.text)

            message_log = (
                f"⚠️ {friendly_error['title']}\n"
                f"{friendly_error['message']}\n\n"
                f"Detalles técnicos: {friendly_error['technical']}"
            )

            intent = "template_error"

        cursor.execute("""
            INSERT INTO whatsapp_messages
                (business_id, phone_number, incoming_message, bot_reply, detected_intent)
            VALUES
                (1, %s, NULL, %s, %s)
        """, (
            phone_number,
            message_log,
            intent
        ))

        conn.commit()

        return redirect(f"/whatsapp/dashboard/customer/{customer_id}#bottom")

    finally:
        conn.close()

@dashboard_bp.get("/whatsapp/media/<path:filename>")
def serve_whatsapp_media(filename):
    return send_from_directory(
        WHATSAPP_MEDIA_DIR,
        filename,
    )

@dashboard_bp.route("/whatsapp/dashboard/customer/<int:customer_id>/messages")
def customer_messages_partial(customer_id):
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                phone_number
            FROM customers
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        if not customer:
            return ""

        cursor.execute("""
            SELECT
                wm.id,
                wm.incoming_message,
                wm.bot_reply,
                wm.detected_intent,
                wm.created_at,
                media.media_type,
                media.mime_type,
                media.local_path
            FROM whatsapp_messages wm
            LEFT JOIN whatsapp_media media
                ON media.message_id = wm.id
            WHERE wm.business_id = 1
              AND wm.phone_number = %s
            ORDER BY wm.created_at ASC
        """, (customer["phone_number"],))

        messages = cursor.fetchall()

        return render_template(
            "components/chat_messages.html",
            messages=messages,
        )

    finally:
        conn.close()

@dashboard_bp.get("/whatsapp/dashboard/services")
def dashboard_services():
    business = get_default_business()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM services
                WHERE business_id = %s
                ORDER BY service_name ASC
                """,
                (business["id"],),
            )
            items = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="services",
        page_title="Servicios",
        page_description=f"Servicios configurados para {business['business_name']}.",
        items=items,
    )


@dashboard_bp.get("/whatsapp/dashboard/reports")
def dashboard_reports():
    business = get_default_business()

    return render_template(
        "simple_page.html",
        business=business,
        active_page="reports",
        page_title="Reportes",
        page_description=(
            "Próximamente: clientes nuevos, servicios más vendidos e ingresos."
        ),
        items=[],
    )


@dashboard_bp.route("/whatsapp/dashboard/settings", methods=["GET", "POST"])
def dashboard_settings():
    business = get_default_business()

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        business_type = request.form.get("business_type", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        active = 1 if request.form.get("active") == "1" else 0

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE businesses
                    SET business_name = %s,
                        business_type = %s,
                        owner_name = %s,
                        phone_number = %s,
                        active = %s
                    WHERE id = %s
                    """,
                    (
                        business_name,
                        business_type,
                        owner_name,
                        phone_number,
                        active,
                        business["id"],
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        business = get_default_business()

    return render_template(
        "settings.html",
        business=business,
        active_page="settings",
    )

# Importa los módulos separados para registrar sus rutas.
from routes.dashboard import agenda, daily_menu, food_catalog, wellness_programs  # noqa: E402,F401
