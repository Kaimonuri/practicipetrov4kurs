from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField('ФИО', max_length=200)
    phone = models.CharField('Телефон', max_length=17)

    def __str__(self):
        return self.full_name or self.user.username
