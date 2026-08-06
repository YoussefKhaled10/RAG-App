from celery_app import celery_app


@celery_app.task(name="tasks.test.add")
def add(x, y):
    return x + y


@celery_app.task(name="tasks.test.ping")
def ping():
    return "pong"