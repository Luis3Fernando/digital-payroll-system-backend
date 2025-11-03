from django.db import models
from common.base_models import BaseModel
from apps.profiles.models import Profile


class Payslip(BaseModel):
    VIEW_STATUS_CHOICES = (
        ('unseen', 'Unseen'),
        ('seen', 'Seen'),
        ('downloaded', 'Downloaded'),
    )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='payslips')
    issue_date = models.DateField()
    pdf_file = models.CharField(max_length=255)
    view_status = models.CharField(max_length=20, choices=VIEW_STATUS_CHOICES, default='unseen')

    concept = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    data_source = models.CharField(max_length=100)
    payroll_type = models.CharField(max_length=100)
    data_type = models.CharField(max_length=50)
    position_order = models.PositiveIntegerField()

    worked_days = models.PositiveIntegerField(default=0)
    non_worked_days = models.PositiveIntegerField(default=0)
    worked_hours = models.PositiveIntegerField(default=0)
    discount_academic_hours = models.PositiveIntegerField(default=0)
    discount_lateness = models.PositiveIntegerField(default=0)
    personal_leave_hours = models.PositiveIntegerField(default=0)
    sunday_discount = models.PositiveIntegerField(default=0)
    vacation_days = models.PositiveIntegerField(default=0)
    vacation_hours = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Payslip for {self.profile.dni} - {self.issue_date}"
