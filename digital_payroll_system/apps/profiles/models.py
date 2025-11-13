from django.db import models
from django.contrib.auth.models import User
from common.base_models import BaseModel

class Profile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True
    )

    ROLE_CHOICES = (
        ('user', 'User'),
        ('admin', 'Admin'),
    )
    last_login = models.DateTimeField(null=True, blank=True)

    dni = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    position = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    descriptionSP = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    resigned_date = models.DateField(null=True, blank=True)
    resigned = models.BooleanField(default=False)

    regimen = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    condition = models.CharField(max_length=100, null=True, blank=True)
    identification_code = models.CharField(max_length=100, null=True, blank=True)
    establishment = models.CharField(max_length=150, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'No User'} ({self.dni})"

class ProfileWorkDetails(BaseModel):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='work_details')

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
        return f"Work details for {self.profile.user.get_full_name() or self.profile.dni}"