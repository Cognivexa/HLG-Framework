# Design Patterns

## Dependency Injection Over Statics

Pass collaborators through the constructor rather than reaching for a static factory or a global container mid-method — it makes every dependency visible in the type signature and trivially mockable in tests.

## Repository Pattern

Wrap persistence behind an interface so business logic doesn't depend on a specific ORM or query builder:

```php
interface OrderRepository
{
    public function find(string $id): ?Order;
    public function save(Order $order): void;
}
```

Keep the interface's methods expressed in domain terms (`markPaid`, not `updateColumn`) so swapping the storage engine never touches calling code.

## Value Objects

Model a domain concept that has no identity of its own (money, an email address, a date range) as an immutable value object rather than a primitive. This moves validation to one place (the constructor) instead of scattering `if`-checks everywhere the primitive is used.

## When to Avoid a Pattern

Introducing a factory, a strategy, or an abstract base class for a single concrete implementation adds indirection without a corresponding benefit. Reach for a pattern when there's a real, current need for the flexibility it buys — a second implementation that already exists, or a seam a test genuinely needs — not because the codebase might need it later.
