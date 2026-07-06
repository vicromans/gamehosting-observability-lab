def only_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def phone_variants(phone_number):
    digits = only_digits(phone_number)
    variants = {digits}

    # México: antes se usaba +52 1 para celulares.
    # Ahora muchos números pueden venir como 52XXXXXXXXXX o 521XXXXXXXXXX.
    if digits.startswith("521") and len(digits) == 13:
        variants.add("52" + digits[3:])

    if digits.startswith("52") and not digits.startswith("521") and len(digits) == 12:
        variants.add("521" + digits[2:])

    return list(variants)
