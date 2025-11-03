from django.contrib import admin
from django.utils.html import format_html
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'profile_display',
        'action',
        'description_short',
        'created_at',
    )

    search_fields = (
        'profile__first_name',
        'profile__last_name',
        'profile__dni',
        'action',
        'description',
    )

    list_filter = (
        'created_at',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'profile',
        'action',
        'description',
        'created_at',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile')

    def profile_display(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}" if obj.profile else "System"
    profile_display.short_description = "Profile"

    def description_short(self, obj):
        return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
    description_short.short_description = "Description"
