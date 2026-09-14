from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_aware_datetime(value):
    if timezone.is_naive(value):
        raise ValidationError("Informe data e horário com fuso explícito.")


class Appointment(models.Model):
    scheduled_at = models.DateTimeField(validators=[validate_aware_datetime])
    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.PROTECT, related_name="appointments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["professional", "scheduled_at"], name="unique_professional_scheduled_at"
            )
        ]

    def __str__(self):
        return f"Consulta {self.pk} — profissional {self.professional_id}"
