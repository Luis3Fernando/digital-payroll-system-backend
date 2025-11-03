from django.contrib import admin
from .models import Payslip

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        'profile',
        'issue_date',
        'concept',
        'amount',
        'view_status',
        'payroll_type',
        'data_source',
        'created_at',
    )

    search_fields = (
        'profile__dni',
        'profile__user__username',
        'profile__user__email',
        'concept',
        'data_source',
        'payroll_type',
    )

    list_filter = (
        'view_status',
        'payroll_type',
        'data_type',
        'issue_date',
    )
    readonly_fields = ('created_at',)

    ordering = ('-issue_date',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile', 'profile__user')

    def profile_name(self, obj):
        return f"{obj.profile.user.get_full_name()}" if obj.profile and obj.profile.user else "No linked profile"
    profile_name.short_description = 'Employee'

    def amount_display(self, obj):
        return f"S/ {obj.amount:,.2f}"
    
    amount_display.short_description = 'Amount'
