from drf_spectacular.utils import OpenApiExample, extend_schema_serializer

from core.serializers import StrictModelSerializer

from .models import Professional
from .validators import normalize_phone, normalize_postal_code


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Profissional com endereço de atendimento",
            request_only=True,
            value={
                "social_name": "Alex",
                "profession": "Psicologia",
                "contact_email": "alex@example.test",
                "contact_phone": "(11) 91234-5678",
                "postal_code": "01001-000",
                "street": "Praça da Sé",
                "number": "s/n",
                "complement": "",
                "neighborhood": "Sé",
                "city": "São Paulo",
                "state": "SP",
            },
        )
    ]
)
class ProfessionalSerializer(StrictModelSerializer):
    class Meta:
        model = Professional
        fields = [
            "id",
            "social_name",
            "profession",
            "contact_email",
            "contact_phone",
            "postal_code",
            "street",
            "number",
            "complement",
            "neighborhood",
            "city",
            "state",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "contact_phone": {"help_text": "Telefone brasileiro com DDD; normalizado para E.164."},
            "postal_code": {"help_text": "Oito dígitos, com ou sem hífen; salvo sem hífen."},
            "number": {"help_text": "Número textual, incluindo valores como 123A ou s/n."},
        }

    def validate_contact_phone(self, value):
        return normalize_phone(value)

    def validate_postal_code(self, value):
        return normalize_postal_code(value)
