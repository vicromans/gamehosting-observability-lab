from services.catalog.media import CATALOG_MEDIA


def normalize_text(text):
    return (text or "").lower().strip()


def get_catalog_keywords(item_key, item):
    keywords = set()

    keywords.add(item_key)

    title = item.get("title")
    if title:
        keywords.add(title.lower())

    for keyword in item.get("keywords", []):
        keywords.add(keyword.lower())

    return keywords


def detect_catalog_item(message):
    text = normalize_text(message)

    for item_key, item in CATALOG_MEDIA.items():
        if not item.get("enabled", True):
            continue

        for keyword in get_catalog_keywords(item_key, item):
            if keyword and keyword in text:
                return item_key

    return None
