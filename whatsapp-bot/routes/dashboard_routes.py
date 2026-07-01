from flask import Blueprint, jsonify, render_template

from database.connection import get_db_connection
from datetime import datetime
from zoneinfo import ZoneInfo

dashboard_bp = Blueprint("dashboard", __name__)


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
