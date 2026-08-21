# Testing

## Feature Tests

A Feature test drives the application through HTTP, the same way a real client would — prefer it over a Unit test whenever the behavior under test involves routing, middleware, or the database:

```php
public function test_authenticated_user_can_create_order(): void
{
    $user = User::factory()->create();
    $response = $this->actingAs($user)->postJson('/api/orders', [
        'items' => [['product_id' => Product::factory()->create()->id, 'quantity' => 2]],
    ]);
    $response->assertCreated();
    $this->assertDatabaseHas('orders', ['user_id' => $user->id]);
}
```

## Database Transactions

Use the `RefreshDatabase` trait so each test runs in a transaction that rolls back at the end — tests stay isolated without needing to manually clean up rows they created.

## Mocking External Services

Fake Laravel's own facades instead of mocking HTTP clients by hand:

```php
Http::fake(['payments.example.com/*' => Http::response(['status' => 'ok'], 200)]);
Mail::fake();
Queue::fake();
```

Then assert on the fake (`Mail::assertSent(OrderConfirmed::class)`) rather than on internal implementation details.

## Factories Over Fixtures

Prefer a model factory with explicit overrides for the fields the test cares about, over a large fixture file — it keeps the setup next to the assertion and makes it obvious which values actually matter for the test.
