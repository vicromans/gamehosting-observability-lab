from flask import Blueprint, jsonify

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/health")
@dashboard_bp.get("/whatsapp/health")
def health():
    return jsonify({"status": "ok", "service": "whatsapp-bot"})
