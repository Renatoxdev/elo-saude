from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["id", "professional", "scheduled_at"]
    list_select_related = ["professional"]
    readonly_fields = ["created_at", "updated_at"]
