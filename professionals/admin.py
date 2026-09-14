from django.contrib import admin

from .models import Professional


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ["social_name", "profession", "city", "state"]
    search_fields = ["social_name", "profession"]
    readonly_fields = ["created_at", "updated_at"]
