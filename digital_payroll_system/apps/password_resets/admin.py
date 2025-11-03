from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import PasswordReset

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = (
        'profile',
        'token',
        'used',
        'is_expired_display',
        'expires_at',
        'created_at',
    )

    search_fields = (
        'profile__dni',
        'profile__user__username',
        'profile__user__email',
        'token',
    )

    list_filter = (
        'used',
        'expires_at',
    )

    readonly_fields = (
        'token',
        'created_at',
    )

    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile', 'profile__user')

    def is_expired_display(self, obj):
        now = timezone.now()
        if obj.expires_at and obj.expires_at < now:
            return format_html('<span style="color: red;">● Expired</span>')
        else:
            return format_html('<span style="color: green;">● Valid</span>')
    is_expired_display.short_description = "Token Status"
