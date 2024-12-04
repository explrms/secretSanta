from celery import Celery
from celery.schedules import crontab

app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

app.conf.update(
    result_backend="redis://localhost:6379/0",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Novosibirsk",
    enable_utc=True,
    beat_schedule={
        # 'subscription_autopay': {   # Автопродление за сутки до окончания подписки
        #     'task': 'celery_app.tasks_payment.subscription_autopay',
        #     'schedule': 60,
        #     # 'args': (16, 16)
        # },
    },
)

app.autodiscover_tasks(["celery_app"])
