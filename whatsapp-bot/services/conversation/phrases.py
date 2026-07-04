AFFIRMATIVE_WORDS = [
    "si",
    "sí",
    "claro",
    "va",
    "sale",
    "ok",
    "okay",
    "okey",
    "perfecto",
    "excelente",
    "me interesa",
    "quiero",
    "sí quiero",
    "si quiero",
    "adelante",
    "hagamoslo",
    "hagámoslo",
]

NEGATIVE_WORDS = [
    "no",
    "no gracias",
    "mejor no",
    "despues",
    "después",
    "luego",
    "mas tarde",
    "más tarde",
    "ahorita no",
]

CLOSING_WORDS = [
    "ok",
    "okay",
    "okey",
    "perfecto",
    "excelente",
    "gracias",
    "muchas gracias",
    "sale",
    "va",
    "listo",
    "esta bien",
    "está bien",
    "👍",
]


def contains_any(text, words):
    normalized = text.lower().strip()
    return any(word in normalized for word in words)


def is_affirmative(text):
    return contains_any(text, AFFIRMATIVE_WORDS)


def is_negative(text):
    return contains_any(text, NEGATIVE_WORDS)


def is_closing(text):
    return contains_any(text, CLOSING_WORDS)
