from celery import shared_task

from .utils.utils import sync_validators


@shared_task(bind=True)
def sync_validators_task(self):
    try:
        sync_validators()
    except Exception as e:
        self.retry(exc=e, countdown=10, max_retries=2)
