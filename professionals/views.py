from django.db import transaction
from rest_framework.viewsets import ModelViewSet

from .models import Professional
from .serializers import ProfessionalSerializer


class ProfessionalViewSet(ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()
