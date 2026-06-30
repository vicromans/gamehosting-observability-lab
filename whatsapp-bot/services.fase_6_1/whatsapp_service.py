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
