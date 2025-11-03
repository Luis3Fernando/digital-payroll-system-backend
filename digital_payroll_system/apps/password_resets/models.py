from django.db import models
from common.base_models import BaseModel
from apps.profiles.models import Profile

class PasswordReset(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"Password reset for {self.profile.dni} ({'used' if self.used else 'pending'})"
