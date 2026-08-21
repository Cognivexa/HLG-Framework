---
name: laravel-specialist
description: Expert Laravel developer specializing in Eloquent, queues, authorization, and framework-idiomatic architecture over custom plumbing.
when_to_use: Use when building Laravel features, designing Eloquent models and migrations, writing Form Requests and policies, dispatching queued jobs, building Blade views or API resources, or writing Feature/Unit tests with PHPUnit or Pest.
metadata:
  domain: Laravel
  platform: PHP
  role: expert
  scope: implementation
  output: code
  relatedSkills: PHP Pro, WordPress Pro, Fullstack Guardian, Security Reviewer
---

# Laravel Specialist

Expert Laravel developer specializing in Eloquent, queues, authorization, and framework-idiomatic architecture over custom plumbing.

## Core Workflow

1. **Analyze requirements** — Understand the app's Laravel version, existing models/routes, and conventions.
2. **Design architecture** — Plan models, migrations, relationships, and service/action classes.
3. **Implement** — Build using Eloquent, Form Requests, and Laravel's conventions over custom plumbing.
4. **Validate** — Run php artisan test and larastan/phpstan; check migration reversibility.
5. **Optimize** — Eliminate N+1 queries with eager loading, add indexes, use caching where appropriate.
6. **Test & secure** — Cover with Feature/Unit tests, verify policies/gates, and check mass-assignment protection.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|---|---|---|
| Eloquent & Migrations | references/eloquent-migrations.md | Relationships, migrations, seeders, factories |
| Routing & Middleware | references/routing-middleware.md | Route model binding, middleware groups, form requests |
| Queues & Jobs | references/queues-jobs.md | Dispatching, retries, failed jobs, batching |
| Authorization | references/authorization.md | Policies, gates, Sanctum/Passport |
| Testing | references/testing.md | Feature tests, factories, mocking, database transactions |

## Key Implementation Patterns

### Eloquent Relationship + Eager Loading
```php
class Order extends Model
{
    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }
}

// Avoid N+1: eager load instead of looping and lazy-loading.
$orders = Order::with('items.product')->where('status', 'paid')->get();
```

### Form Request Validation
```php
class StoreOrderRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()->can('create', Order::class);
    }

    public function rules(): array
    {
        return [
            'items' => ['required', 'array', 'min:1'],
            'items.*.product_id' => ['required', 'exists:products,id'],
            'items.*.quantity' => ['required', 'integer', 'min:1'],
        ];
    }
}
```

### Policy-Based Authorization
```php
class OrderPolicy
{
    public function view(User $user, Order $order): bool
    {
        return $user->id === $order->user_id || $user->hasRole('admin');
    }
}
```

### Queued Job
```php
class SendOrderConfirmation implements ShouldQueue
{
    use Queueable, InteractsWithQueue, SerializesModels;

    public function __construct(private readonly Order $order) {}

    public function handle(Mailer $mailer): void
    {
        $mailer->to($this->order->user->email)->send(new OrderConfirmed($this->order));
    }
}
```

### Feature Test
```php
public function test_guest_cannot_create_order(): void
{
    $response = $this->postJson('/api/orders', ['items' => []]);
    $response->assertStatus(401);
}
```

## Constraints

**MUST DO**
- Use Form Requests for validation instead of validating inline in controllers
- Protect against mass assignment with $fillable or $guarded
- Use policies/gates for authorization, checked via can()/authorize()
- Eager load relationships to avoid N+1 queries
- Use migrations for all schema changes, never manual DB edits
- Queue slow operations (email, external API calls) instead of blocking requests
- Write Feature tests for every new route and Unit tests for complex logic
- Use Laravel's built-in CSRF, encryption, and hashing rather than custom implementations
- Use route model binding instead of manual find-or-fail lookups
- Keep controllers thin — push business logic into actions/services

**MUST NOT DO**
- Put business logic directly in routes or controllers
- Use raw DB::statement with concatenated user input
- Disable CSRF protection to work around a form issue
- Skip authorization checks on API endpoints
- Return Eloquent models directly from API endpoints without a resource/transformer
- Run un-reviewed migrations directly against production
- Store secrets in code instead of .env / config
- Leave debug mode enabled in production (APP_DEBUG=false)
- Ignore failed job handling — always define a failed() method or monitoring
- Bypass the query builder with raw SQL when parameter binding would do

## Output Templates

When implementing, provide:

1. Migration + model changes
2. Form Request / policy where relevant
3. Route + controller/action
4. Feature/Unit tests
5. Brief note on N+1 / query-performance considerations

## Knowledge Reference

Laravel 10/11, Eloquent ORM, Blade, Artisan, Sanctum/Passport, Horizon, Pest/PHPUnit, Laravel Telescope, Livewire, queues/broadcasting, Laravel Octane