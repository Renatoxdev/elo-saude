from django import forms
from django_filters import rest_framework as filters

from .models import Appointment


class ProfessionalIDFilter(filters.Filter):
    field_class = forms.IntegerField


class AppointmentFilter(filters.FilterSet):
    professional_id = ProfessionalIDFilter(field_name="professional_id", min_value=1)

    class Meta:
        model = Appointment
        fields = ["professional_id"]
