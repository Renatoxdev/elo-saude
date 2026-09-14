from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from .filters import AppointmentFilter
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(ModelViewSet):
    queryset = Appointment.objects.select_related("professional").all()
    serializer_class = AppointmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AppointmentFilter

    def filter_queryset(self, queryset):
        if (
            "professional_id" in self.request.query_params
            and not self.request.query_params["professional_id"].strip()
        ):
            raise ValidationError({"professional_id": ["Informe um ID inteiro positivo."]})
        return super().filter_queryset(queryset)

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save()
