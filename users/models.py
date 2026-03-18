from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    provider = models.ForeignKey(
        "billing.Provider",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return self.username
