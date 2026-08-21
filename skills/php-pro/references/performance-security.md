# Performance & Security

## OPcache

Enable and preload OPcache in production (`opcache.enable=1`, `opcache.validate_timestamps=0` with a deploy-time cache clear) — without it, PHP recompiles every file on every request. Never disable timestamp validation on a machine where files still change live (local dev).

## N+1 Queries

Loading a collection and then querying inside the loop for each item's related data is the single most common PHP performance bug:

```php
// N+1: one query per order
foreach ($orders as $order) {
    $items = $itemRepository->findByOrderId($order->id);
}

// One query for all of them
$itemsByOrder = $itemRepository->findByOrderIds(array_column($orders, 'id'));
```

## Prepared Statements

Always bind parameters rather than interpolating values into a query string, even for values that "can't" contain attacker input — the cost of prepared statements is negligible and the alternative is one refactor away from a SQL injection.

## Deserialization Risks

`unserialize()` on attacker-controlled data can instantiate arbitrary objects and trigger their `__wakeup`/`__destruct` methods (PHP object injection). Use `json_decode`/`json_encode` for any data that crosses a trust boundary, and reserve `serialize`/`unserialize` for data your own application fully controls end to end.

## Profiling

Reach for Xdebug's profiler or Blackfire when a request is slow and the cause isn't obvious from logs — guessing at optimizations without a profile usually optimizes the wrong function.
