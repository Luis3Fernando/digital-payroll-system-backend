from django.db import models
from common.base_models import BaseModel
from apps.profiles.models import Profile

class AuditLog(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"[{self.created_at}] {self.action} - {self.profile}"
