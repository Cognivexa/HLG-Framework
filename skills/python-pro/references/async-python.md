# Async Python

## When to Reach for asyncio

Async I/O helps when a program spends most of its time waiting on network or disk I/O and needs to juggle many such waits concurrently (an API client fetching from many endpoints, a web server handling many connections). It does not speed up CPU-bound work — the GIL still serializes actual Python bytecode execution within one process.

## async/await Basics

```python
async def fetch_user(client: httpx.AsyncClient, user_id: int) -> dict:
    response = await client.get(f"/users/{user_id}")
    response.raise_for_status()
    return response.json()
```

## Concurrency with gather

```python
results = await asyncio.gather(*(fetch_user(client, uid) for uid in user_ids))
```

`asyncio.gather` runs all the awaitables concurrently and raises the first exception once all have completed (or use `return_exceptions=True` to collect them all instead of failing fast).

## Common Pitfalls

- Calling a blocking, synchronous function (a CPU-bound loop, a non-async DB driver) inside an async function still blocks the entire event loop — offload it with `asyncio.to_thread` or a process pool.
- Forgetting to `await` a coroutine creates it without running it, and Python only warns about this after the fact (a "coroutine was never awaited" warning).
- Mixing sync and async database drivers for the same connection pool causes subtle deadlocks; pick one consistently per codebase.

## Structured Concurrency

Prefer `asyncio.TaskGroup` (3.11+) over manually tracking a list of `create_task` results — it ensures all child tasks are awaited and cancelled together if one fails, rather than leaking an orphaned task.
