import re

import phonenumbers
from django.core.exceptions import ValidationError

BRAZILIAN_STATES = tuple(
    (state, state)
    for state in (
        "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO"
    ).split()
)


def validate_nonblank(value):
    if not value.strip():
        raise ValidationError("Informe um valor que não seja apenas espaços.")


def normalize_postal_code(value):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{5}-?[0-9]{3}", value):
        raise ValidationError("Informe um CEP com oito dígitos, com ou sem hífen.")
    return value.replace("-", "")


def validate_postal_code(value):
    normalize_postal_code(value)


def normalize_phone(value):
    value = value.strip()
    if not re.fullmatch(r"\+?[0-9 ()-]+", value):
        raise ValidationError("Informe um telefone brasileiro com DDD.")
    try:
        number = phonenumbers.parse(value, "BR")
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Informe um telefone brasileiro com DDD.") from exc
    if not phonenumbers.is_valid_number_for_region(number, "BR"):
        raise ValidationError("Informe um telefone brasileiro válido com DDD.")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def validate_phone(value):
    normalize_phone(value)
