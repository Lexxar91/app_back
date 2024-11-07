from celery import Celery


celery_app = Celery(
    'background_tasks',
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(result_expires=60)
celery_app.autodiscover_tasks(['app.crud.patents_export.py'])