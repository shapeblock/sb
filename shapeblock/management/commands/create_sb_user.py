import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create a superuser non-interactively if it does not exist'

    def handle(self, *args, **kwargs):
        username = os.environ.get('SB_USERNAME')
        email = os.environ.get('SB_USER_EMAIL')
        password = os.environ.get('SB_USER_PASSWORD')

        if not username or not email or not password:
            self.stdout.write(self.style.ERROR('Environment variables SB_USERNAME, SB_USER_EMAIL, and SB_USER_PASSWORD must be set'))
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Successfully created ruser {username}'))
