from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from professionals.validators import normalize_postal_code

from .serializers import AddressSerializer
from .services import lookup_postal_code


class PostalCodeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "postal_code"

    @extend_schema(
        responses=AddressSerializer,
        description="Consulta auxiliar ViaCEP. Aceita CEP com ou sem hífen; não salva o endereço.",
    )
    def get(self, request, postal_code):
        try:
            postal_code = normalize_postal_code(postal_code)
        except DjangoValidationError as exc:
            raise ValidationError({"postal_code": exc.messages}) from exc
        return Response(lookup_postal_code(postal_code))
