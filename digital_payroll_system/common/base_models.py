import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Base abstract model providing:
    - UUID primary key
    - created_at and updated_at timestamps
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the record was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the record was last updated."
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"
