from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'profile_display',
        'action',
        'description_short',
        'created_at',
    )

    search_fields = (
        'profile__user__first_name',
        'profile__user__last_name',
        'profile__dni',
        'action',
        'description',
    )

    list_filter = ('created_at',)
    ordering = ('-created_at',)

    readonly_fields = (
        'profile',
        'action',
        'description',
        'created_at',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile__user')

    def profile_display(self, obj):
        if obj.profile and obj.profile.user:
            full_name = f"{obj.profile.user.first_name} {obj.profile.user.last_name}".strip()
            return full_name if full_name else obj.profile.dni
        return "System"
    profile_display.short_description = "Profile"


    def description_short(self, obj):
        return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
    description_short.short_description = "Description"
