import json
import logging

import httpx
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework.exceptions import APIException, NotFound

from professionals.validators import BRAZILIAN_STATES, normalize_postal_code

logger = logging.getLogger(__name__)


class AddressServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Consulta de CEP indisponível. Você pode preencher o endereço manualmente."
    default_code = "address_service_unavailable"


def lookup_postal_code(postal_code):
    key = f"viacep:{postal_code}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        with httpx.Client(timeout=httpx.Timeout(3, connect=2), follow_redirects=False) as client:
            with client.stream(
                "GET", f"{settings.VIACEP_BASE_URL}/{postal_code}/json/"
            ) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes(chunk_size=4096):
                    body.extend(chunk)
                    if len(body) > 32 * 1024:
                        raise ValueError("Provider response too large")
                payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected response shape")
        if payload.get("erro") in (True, "true"):
            raise NotFound("CEP não encontrado.")
        result = {
            "postal_code": normalize_postal_code(payload["cep"]),
            "street": payload["logradouro"],
            "complement": payload.get("complemento", ""),
            "neighborhood": payload["bairro"],
            "city": payload["localidade"],
            "state": payload["uf"],
        }
        if (
            any(not isinstance(value, str) for value in result.values())
            or result["postal_code"] != postal_code
            or result["state"] not in dict(BRAZILIAN_STATES)
            or not result["city"].strip()
        ):
            raise ValueError("Invalid address response")
    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        ValidationError,
    ) as exc:
        logger.warning("address_provider_failure", extra={"event": "address_provider_failure"})
        raise AddressServiceUnavailable() from exc
    cache.set(key, result, timeout=3600)
    return result
