import os
from services.whatsapp_service import send_whatsapp_image
from services.catalog.media import CATALOG_MEDIA


CATALOG_BASE_URL = "https://api.veldriklabs.com/whatsapp/static/catalog"


def get_catalog_item(item_key):
    item = CATALOG_MEDIA.get(item_key)

    if not item:
        return None

    if not item.get("enabled", True):
        return None

    return item


def build_media_url(item):
    image_path = item.get("image")

    if not image_path:
        return None

    return f"{CATALOG_BASE_URL}/{image_path}"


def send_catalog_item(phone_number, item_key):
    item = get_catalog_item(item_key)

    if not item:
        return False

    image_url = build_media_url(item)

    if not image_url:
        return False

    caption = item.get("caption", "")

    send_whatsapp_image(
        phone_number,
        image_url,
        caption,
        os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        os.getenv("WHATSAPP_TOKEN")
    )

    return True
