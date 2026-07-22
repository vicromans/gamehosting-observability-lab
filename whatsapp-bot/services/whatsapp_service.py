import requests


def send_whatsapp_message(to, message, phone_number_id, token):
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print("WHATSAPP SEND STATUS:", response.status_code)
    print("WHATSAPP SEND RESPONSE:", response.text)

    return response


def send_whatsapp_template_message(to, template_name, customer_name, topic, phone_number_id, token):
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "es_MX"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": customer_name
                        },
                        {
                            "type": "text",
                            "text": topic
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print("WHATSAPP TEMPLATE SEND STATUS:", response.status_code)
    print("WHATSAPP TEMPLATE SEND RESPONSE:", response.text)

    return response

def send_whatsapp_image(to, image_url, caption, phone_number_id, token):
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)

    print("WHATSAPP IMAGE SEND STATUS:", response.status_code)
    print("WHATSAPP IMAGE SEND RESPONSE:", response.text)

    return response


def send_human_support_template_message(
    to,
    business_name,
    customer_name,
    reason,
    phone_number_id,
    token,
):
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "human_support_request",
            "language": {
                "code": "es_MX",
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": business_name,
                        },
                        {
                            "type": "text",
                            "text": customer_name,
                        },
                        {
                            "type": "text",
                            "text": reason,
                        },
                    ],
                }
            ],
        },
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10,
    )

    print("WHATSAPP HUMAN TEMPLATE STATUS:", response.status_code)
    print("WHATSAPP HUMAN TEMPLATE RESPONSE:", response.text)

    return response

def download_whatsapp_media(media_id, destination_path, token):
    """
    Descarga un archivo recibido por WhatsApp desde Meta.

    destination_path debe ser la ruta completa donde se guardará el archivo.
    """

    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        metadata_url = f"https://graph.facebook.com/v23.0/{media_id}"

        metadata_response = requests.get(
            metadata_url,
            headers=headers,
            timeout=15,
        )
        metadata_response.raise_for_status()

        metadata = metadata_response.json()
        download_url = metadata.get("url")

        if not download_url:
            return {
                "success": False,
                "error": "Meta no devolvió la URL del archivo.",
            }

        media_response = requests.get(
            download_url,
            headers=headers,
            timeout=30,
        )
        media_response.raise_for_status()

        import os

        destination_directory = os.path.dirname(destination_path)

        if destination_directory:
            os.makedirs(destination_directory, exist_ok=True)

        temporary_path = f"{destination_path}.part"

        with open(temporary_path, "wb") as media_file:
            media_file.write(media_response.content)

        os.replace(temporary_path, destination_path)

        print(
            f"WHATSAPP MEDIA DOWNLOADED "
            f"media_id={media_id} "
            f"path={destination_path} "
            f"bytes={len(media_response.content)}",
            flush=True,
        )

        return {
            "success": True,
            "local_path": destination_path,
            "mime_type": metadata.get("mime_type"),
            "sha256": metadata.get("sha256"),
            "file_size": metadata.get(
                "file_size",
                len(media_response.content),
            ),
        }

    except requests.RequestException as error:
        print(
            f"WHATSAPP MEDIA DOWNLOAD ERROR "
            f"media_id={media_id}: {error}",
            flush=True,
        )

        return {
            "success": False,
            "error": str(error),
        }

    except OSError as error:
        print(
            f"WHATSAPP MEDIA FILE ERROR "
            f"media_id={media_id}: {error}",
            flush=True,
        )

        return {
            "success": False,
            "error": str(error),
        }
