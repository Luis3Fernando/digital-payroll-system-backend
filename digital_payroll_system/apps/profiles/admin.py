from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'dni',
        'get_full_name',
        'role',
        'position',
        'regimen',
        'category',
        'condition',
        'is_active',
        'created_at',
    )

    search_fields = (
        'dni',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'position',
    )

    list_filter = (
        'role',
        'is_active',
        'resigned',
        'regimen',
        'category',
    )

    readonly_fields = ('created_at', 'updated_at')

    ordering = ('-created_at',)

    fields = ('dni', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        if obj.user:
            full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return full_name if full_name else "(No name)"
        return "No linked user"

    get_full_name.short_description = 'Full Name'
