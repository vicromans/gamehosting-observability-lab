from flask import Blueprint, jsonify, send_from_directory

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
@public_bp.get("/whatsapp/")
def index():
    return jsonify({
        "service": "VeldrikLabs WhatsApp Bot",
        "status": "running"
    })


@public_bp.get("/whatsapp/static/<path:filename>")
def whatsapp_static(filename):
    return send_from_directory("static", filename)
