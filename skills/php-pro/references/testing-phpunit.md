# Testing with PHPUnit

## Test Doubles

Prefer a real object over a mock whenever it's cheap to construct — a mock only pays for itself when the real dependency is slow, non-deterministic, or has side effects (network calls, sending email, charging a card).

```php
$gateway = $this->createMock(PaymentGateway::class);
$gateway->method('charge')->willReturn(new Charge('ch_123', 500));
```

## Data Providers

Use a data provider instead of copy-pasting near-identical test methods for different inputs:

```php
#[DataProvider('cases')]
public function testDiscount(int $subtotal, int $expected): void { /* ... */ }

public static function cases(): array
{
    return [
        'no discount below threshold' => [500, 500],
        'discount applied at threshold' => [10000, 9500],
    ];
}
```

Naming each case (the array key) makes failures readable in the test runner output without opening the file.

## Coverage

Treat coverage percentage as a signal for untested areas, not a target to hit for its own sake — 100% line coverage with no assertions on behavior catches nothing. Prioritize covering branches with real business risk (money, permissions, external I/O) over simple getters and setters.

## Database Tests

Wrap each test in a transaction that rolls back afterward (PHPUnit's `RefreshDatabase`-style trait in framework integrations, or a manual `beginTransaction`/`rollBack` in plain PHPUnit) so tests never leak state into each other or require manual cleanup.
