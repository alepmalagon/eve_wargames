"""
Celery application configuration for EVE Wargames.

This module initializes and configures the Celery application
for background task processing.
"""

from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "eve_wargames",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.data_collection']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # Results expire after 1 hour
    # Task expiration and reliability settings
    task_expires=7200,  # Tasks expire after 2 hours to prevent stale task accumulation
    task_acks_late=True,  # Acknowledge tasks only after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker crashes
    # Rate limiting to prevent queue flooding
    task_default_rate_limit='10/m',  # Max 10 tasks per minute per worker
    # Prevent task duplication during downtime
    task_ignore_result=False,  # Keep results for deduplication
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'collect-faction-warfare-data': {
        'task': 'app.tasks.data_collection.collect_faction_warfare_data',
        'schedule': 3600.0,  # Every hour
    },
    'orchestrate-killmail-collection': {
        'task': 'app.tasks.data_collection.orchestrate_killmail_collection',
        'schedule': 3600.0,  # Every hour - starts the staggered collection
    },
    'collect-general-warzone-data': {
        'task': 'app.tasks.data_collection.collect_general_warzone_data',
        'schedule': 3600.0,  # Every hour - collects general warzone data
    },
    'cleanup-old-data': {
        'task': 'app.tasks.data_collection.cleanup_old_data',
        'schedule': 86400.0,  # Daily
        'kwargs': {'days_to_keep': 90}
    },
    'health-check': {
        'task': 'app.tasks.data_collection.health_check_task',
        'schedule': 300.0,  # Every 5 minutes
    },
}

celery_app.conf.timezone = 'UTC'

if __name__ == '__main__':
    celery_app.start()
