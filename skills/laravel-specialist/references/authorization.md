# Authorization

## Policies

A policy centralizes the authorization rules for one model, keyed by action:

```php
class OrderPolicy
{
    public function update(User $user, Order $order): bool
    {
        return $user->id === $order->user_id && $order->status === OrderStatus::Pending;
    }
}
```

Register it (auto-discovered by naming convention in recent Laravel versions, or explicitly in `AuthServiceProvider`), then check it everywhere the action is exposed — a controller, a Blade `@can`, a Livewire component, and an API endpoint must all check the same policy rather than re-implementing the rule.

## Gates

Use a Gate for authorization that isn't tied to a specific model instance:

```php
Gate::define('access-admin-panel', fn (User $user) => $user->hasRole('admin'));
```

## API Authentication: Sanctum vs. Passport

Use Sanctum for a first-party SPA or mobile app talking to your own API (lightweight token or cookie-based auth). Reach for Passport only when you need full OAuth2 — issuing tokens to genuinely third-party clients you don't control.

## Defense in Depth

Authorization belongs at every layer it's checked: the policy is the source of truth, but also scope queries to the current user (`Order::where('user_id', $user->id)`) so a missing `authorize()` call in one code path doesn't turn into an IDOR.
