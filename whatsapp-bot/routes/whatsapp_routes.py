import os

from flask import Blueprint, jsonify, request

from database.connection import get_db_connection
from services.conversation.engine import build_replies
from services.conversation.human import mark_human_required
from services.whatsapp_service import (
    download_whatsapp_media,
    send_whatsapp_message,
)

whatsapp_bp = Blueprint("whatsapp", __name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "veldriklabs_verify_2026")
WHATSAPP_MEDIA_DIR = os.getenv(
    "WHATSAPP_MEDIA_DIR",
    "/app/static/uploads/whatsapp",
)

@whatsapp_bp.get("/webhook")
@whatsapp_bp.get("/whatsapp/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("WEBHOOK VERIFIED", flush=True)
        return challenge, 200

    return "Verification failed", 403


@whatsapp_bp.post("/webhook")
@whatsapp_bp.post("/whatsapp/webhook")
def receive_message():
    data = request.get_json()

    print("=" * 80, flush=True)
    print("INCOMING WHATSAPP WEBHOOK", flush=True)
    print(data, flush=True)
    print("=" * 80, flush=True)

    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        contacts = value.get("contacts", [])
        messages = value.get("messages", [])

        if not messages:
            return jsonify({"status": "no_message"}), 200

        contact = contacts[0] if contacts else {}
        message = messages[0]

        phone_number = message.get("from")
        customer_name = contact.get("profile", {}).get("name")
        message_type = message.get("type", "unknown")
        replies = []
        media_record = None

        if message_type == "text":
            incoming_message = message.get("text", {}).get("body", "")
            replies = build_replies(incoming_message, phone_number)
            reply = "\n\n---\n\n".join([r for r in replies if r])

        elif message_type == "image":
            image_data = message.get("image", {})
            media_id = image_data.get("id")
            caption = image_data.get("caption", "").strip()
            mime_type = image_data.get("mime_type")
            sha256 = image_data.get("sha256")

            local_path = None

            if media_id:
                extension_by_mime = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }

                file_extension = extension_by_mime.get(mime_type, ".bin")
                filename = f"{media_id}{file_extension}"
                destination_path = os.path.join(WHATSAPP_MEDIA_DIR, filename)

                download_result = download_whatsapp_media(
                    media_id,
                    destination_path,
                    WHATSAPP_TOKEN,
                )

                if download_result.get("success"):
                    local_path = f"uploads/whatsapp/{filename}"
                    mime_type = download_result.get("mime_type") or mime_type
                    sha256 = download_result.get("sha256") or sha256
                else:
                    print(
                        f"WHATSAPP MEDIA NOT SAVED "
                        f"media_id={media_id} "
                        f"error={download_result.get('error')}",
                        flush=True,
                    )

            incoming_message = caption or "[Imagen recibida]"
            intent = "image_received"

            mark_human_required(phone_number)

            reply = (
                "Gracias 😊 Recibí tu imagen.\n\n"
                "Ana la revisará y te responderá en breve."
            )
            replies = [reply]

            media_record = {
                "media_type": "image",
                "media_id": media_id,
                "mime_type": mime_type,
                "caption": caption or None,
                "sha256": sha256,
                "local_path": local_path,
            }

            print(
                f"IMAGE RECEIVED from={phone_number} "
                f"media_id={media_id} caption={caption!r}",
                flush=True,
            )

        else:
            incoming_message = f"[Mensaje no compatible: {message_type}]"
            intent = "unsupported_message"

            reply = (
                "Recibí tu mensaje, pero por ahora necesito que me lo envíes "
                "como texto o imagen para poder ayudarte. 😊"
            )
            replies = [reply]

        if reply and "canalizar" in reply:
            mark_human_required(phone_number)

        if message_type == "text":
            intent = "unknown"
            lower_msg = incoming_message.lower()

            if "cita" in lower_msg or "agendar" in lower_msg or "anticipo" in lower_msg:
                intent = "appointment"
            elif "pestana" in lower_msg or "pestaña" in lower_msg or "pestañas" in lower_msg:
                intent = "lashes"
            elif "una" in lower_msg or "uña" in lower_msg or "uñas" in lower_msg or "gel" in lower_msg or "gelish" in lower_msg or "semipermanente" in lower_msg:
                intent = "nails"
            elif "alisado" in lower_msg or "cabello" in lower_msg:
                intent = "hair"
            elif "horario" in lower_msg:
                intent = "schedule"
            elif "precio" in lower_msg or "costo" in lower_msg or "cuanto" in lower_msg or "cuánto" in lower_msg or "$" in lower_msg:
                intent = "pricing"
            elif "hola" in lower_msg or "buenas" in lower_msg:
                intent = "greeting"

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO customers (business_id, phone_number, customer_name)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        customer_name = VALUES(customer_name),
                        last_contact = CURRENT_TIMESTAMP
                """, (1, phone_number, customer_name))

                cursor.execute("""
                    INSERT INTO whatsapp_messages
                    (business_id, phone_number, incoming_message, bot_reply, detected_intent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (1, phone_number, incoming_message, reply, intent))

                message_db_id = cursor.lastrowid

                if media_record and media_record.get("media_id"):
                    cursor.execute("""
                        INSERT INTO whatsapp_media
                        (
                            message_id,
                            business_id,
                            phone_number,
                            media_type,
                            media_id,
                            mime_type,
                            caption,
                            sha256,
                            local_path
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            mime_type = COALESCE(VALUES(mime_type), mime_type),
                            caption = COALESCE(VALUES(caption), caption),
                            sha256 = COALESCE(VALUES(sha256), sha256),
                            local_path = COALESCE(VALUES(local_path), local_path)
                    """, (
                        message_db_id,
                        1,
                        phone_number,
                        media_record["media_type"],
                        media_record["media_id"],
                        media_record["mime_type"],
                        media_record["caption"],
                        media_record["sha256"],
                        media_record["local_path"],
                    ))

            connection.commit()

        finally:
            connection.close()

        print(f"Saved WhatsApp message from {phone_number}: {incoming_message}", flush=True)

        if replies:
            import time

            for outbound_message in replies:
                if not outbound_message:
                    continue

                send_whatsapp_message(
                    phone_number,
                    outbound_message,
                    WHATSAPP_PHONE_NUMBER_ID,
                    WHATSAPP_TOKEN
                )

                time.sleep(0.7)

        return jsonify({
            "status": "saved",
            "phone_number": phone_number,
            "message": incoming_message,
            "intent": intent
        }), 200

    except Exception as e:
        print("ERROR processing webhook:", str(e), flush=True)
        return jsonify({"status": "error", "error": str(e)}), 200
