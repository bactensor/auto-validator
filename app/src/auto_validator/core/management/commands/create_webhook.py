import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Create a GitHub webhook for the repository'

    def handle(self, *args, **kwargs):
        self.create_webhook()

    def create_webhook(self):
        url = f'https://api.github.com/repos/{settings.REPO_OWNER}/{settings.REPO_NAME}/hooks'
        headers = {
            'Authorization': f'token {settings.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        payload = {
            'name': 'web',
            'active': True,
            'events': ['pull_request'],
            'config': {
                'url': settings.WEBHOOK_URL,
                'content_type': 'json'
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS('Webhook created successfully'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to create webhook: {response.content}'))