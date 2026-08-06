from celery import Celery
from helpers.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.test",
        "tasks.file_processing",
    ],
)

celery_app.conf.update(
    task_serializer=getattr(settings, "CELERY_TASK_SERIALIZER", "json"),
    result_serializer=getattr(settings, "CELERY_TASK_SERIALIZER", "json"),
    accept_content=[getattr(settings, "CELERY_TASK_SERIALIZER", "json")],

    task_track_started=True,

    task_acks_late=getattr(settings, "CELERY_TASK_ACKS_LATE", True),
    task_reject_on_worker_lost=getattr(settings, "CELERY_TASK_REJECT_ON_WORKER_LOST", True),
    worker_prefetch_multiplier=getattr(settings, "CELERY_WORKER_PREFETCH_MULTIPLIER", 1),

    task_time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT", 600),
    task_ignore_result=False,
    result_expires=3600,

    worker_concurrency=getattr(settings, "CELERY_WORKER_CONCURRENCY", 1),

    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    task_routes={
        "tasks.file_processing.process_uploaded_file": {
            "queue": "file_processing"
        }
    },
)

celery_app.conf.task_default_queue = "default"