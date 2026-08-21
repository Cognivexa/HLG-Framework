# Background Tasks

## Celery Tasks

Dispatch anything slow or calling an external service as a Celery task instead of doing it inline in the request-response cycle:

```python
send_order_confirmation.delay(order.id)
```

Pass primitive IDs, not model instances, as task arguments — Celery serializes arguments (typically to JSON), and a model instance can go stale between when the task is queued and when it runs.

## Retries

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def charge_payment(self, order_id):
    try:
        ...
    except PaymentGatewayTimeout as exc:
        raise self.retry(exc=exc)
```

Make tasks idempotent — Celery's at-least-once delivery means a task can run more than once; check "already done" state before repeating a side effect like charging a card or sending an email.

## Signals

Use Django signals (`post_save`, `pre_delete`) sparingly — they make control flow implicit and harder to trace. Prefer calling a service function explicitly from the view or model method unless the side effect genuinely needs to fire regardless of which code path triggered the save.

## Scheduled Jobs

Use Celery Beat (or the equivalent scheduler) for periodic tasks, and make each scheduled task safe to run concurrently or skip if a previous run is still in progress (a lock via cache or a "last run" timestamp check).
