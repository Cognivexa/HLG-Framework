# Queues & Jobs

## Dispatching

```php
SendOrderConfirmation::dispatch($order);
SendOrderConfirmation::dispatch($order)->onQueue('emails')->delay(now()->addMinutes(5));
```

Dispatch anything that calls an external service (email, SMS, payment webhooks, third-party APIs) as a job instead of doing it inline in the request — a slow or down third party should never make your own endpoint time out.

## Retries & Backoff

```php
class SendOrderConfirmation implements ShouldQueue
{
    public int $tries = 3;
    public function backoff(): array
    {
        return [10, 60, 300]; // seconds between attempts
    }
}
```

Make job handling idempotent — a retried job must be safe to run again (check "already sent" state, use upserts) since Laravel's at-least-once delivery means a job can run more than once.

## Failed Jobs

Always define a `failed()` method or wire up `Queue::failing()` monitoring — a job that silently exhausts its retries and vanishes into the `failed_jobs` table is a production incident nobody noticed.

```php
public function failed(Throwable $exception): void
{
    Log::error('Order confirmation failed permanently', ['order_id' => $this->order->id]);
}
```

## Batching

Group related jobs and react to the batch as a whole when you need "all of these succeeded" semantics:

```php
Bus::batch([new ProcessOrder($a), new ProcessOrder($b)])
    ->then(fn (Batch $batch) => Log::info('Batch complete'))
    ->catch(fn (Batch $batch, Throwable $e) => Log::error('Batch had a failure'))
    ->dispatch();
```
