from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Создаёт или обновляет администратора Lab16 с паролем Prac4 по требованиям практической работы.'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username='Lab16')
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password('Prac4')
        user.save()
        action = 'создан' if created else 'обновлён'
        self.stdout.write(self.style.SUCCESS(f'Администратор Lab16 {action}.'))
