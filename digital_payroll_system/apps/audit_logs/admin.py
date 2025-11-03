from django.contrib import admin
from django.utils.html import format_html
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_display',
        'action_type_display',
        'action',
        'description_short',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'action',
        'description',
    )

    list_filter = (
        'action_type',
        'created_at',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'user',
        'action_type',
        'action',
        'description',
        'created_at',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    def action_type_display(self, obj):
        color_map = {
            'info': 'color: #007bff;',
            'warning': 'color: #ffc107;',
            'error': 'color: #dc3545;',
        }
        color = color_map.get(obj.action_type, 'color: #6c757d;') 
        return format_html(f'<strong style="{color}">● {obj.action_type.upper()}</strong>')
    action_type_display.short_description = "Type"

    def user_display(self, obj):
        return obj.user.username if obj.user else "System"
    user_display.short_description = "User"

    def description_short(self, obj):
        return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
    description_short.short_description = "Description"
