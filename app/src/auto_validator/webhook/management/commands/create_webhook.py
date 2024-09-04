# webhook/management/commands/register_webhook.py
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Register GitHub webhook'

    def handle(self, *args, **kwargs):
        url = f'https://api.github.com/repos/{settings.REPO_OWNER}/{settings.REPO_NAME}/hooks'
        payload = {
            'name': 'web',
            'active': True,
            'events': ['pull_request'],
            'config': {
                'url': f'{settings.WEBHOOK_URL}/webhook/',
                'content_type': 'json',
                'secret': settings.GITHUB_SECRET,
            }
        }
        headers = {
            'Authorization': f'token {settings.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS('Successfully registered webhook'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to register webhook: {response.content}'))