from flask import Blueprint, jsonify, render_template

from database.connection import get_db_connection

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
