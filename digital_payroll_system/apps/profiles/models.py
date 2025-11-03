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

    dni = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    position = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    resigned = models.BooleanField(default=False)

    regimen = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    condition = models.CharField(max_length=100, null=True, blank=True)
    identification_code = models.CharField(max_length=100, null=True, blank=True)
    establishment = models.CharField(max_length=150, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'No User'} ({self.dni})"
