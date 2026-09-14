from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from core.exceptions import Conflict
from core.serializers import StrictModelSerializer

from .models import Appointment


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        try:
            parsed = parse_datetime(value) if isinstance(value, str) else None
        except ValueError:
            parsed = None
        if parsed is None or timezone.is_naive(parsed):
            raise serializers.ValidationError("Informe data e horário ISO 8601 com fuso explícito.")
        return super().to_internal_value(value)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Consulta com fuso explícito",
            request_only=True,
            description="Substitua professional pelo ID retornado ao cadastrar o profissional.",
            value={"professional": 1, "scheduled_at": "2020-01-02T09:00:00-03:00"},
        )
    ]
)
class AppointmentSerializer(StrictModelSerializer):
    scheduled_at = AwareDateTimeField(
        help_text="ISO 8601 com fuso. Histórico permitido; conflito no mesmo instante: 409."
    )

    class Meta:
        model = Appointment
        fields = ["id", "scheduled_at", "professional", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        professional = attrs.get("professional", getattr(self.instance, "professional", None))
        scheduled_at = attrs.get("scheduled_at", getattr(self.instance, "scheduled_at", None))
        queryset = Appointment.objects.filter(professional=professional, scheduled_at=scheduled_at)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise Conflict("Este profissional já tem uma consulta nesse instante.")
        return attrs
