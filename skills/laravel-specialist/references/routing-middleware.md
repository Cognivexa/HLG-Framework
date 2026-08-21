# Routing & Middleware

## Route Model Binding

Let Laravel resolve the model instead of manually calling `findOrFail`:

```php
Route::get('/orders/{order}', [OrderController::class, 'show']);

public function show(Order $order) { /* $order is already resolved, or a 404 was thrown */ }
```

Use scoped bindings (`Route::get('/users/{user}/orders/{order}')->scopeBindings()`) when a nested resource must belong to its parent, so one user can't fetch another's order by guessing an ID.

## Middleware Groups

Group related middleware instead of listing them individually on every route:

```php
Route::middleware(['auth:sanctum', 'throttle:api'])->group(function () {
    Route::apiResource('orders', OrderController::class);
});
```

## Form Requests as the Validation Boundary

A Form Request is both the validation rules and the authorization check for a route in one class — inject it as the controller method's parameter and Laravel validates before the method body runs, so the method can assume its input is already valid.

## API Resources

Never return an Eloquent model directly from a JSON endpoint — wrap it in a Resource so the response shape is explicit and stable even if the underlying model gains columns later:

```php
class OrderResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'totalCents' => $this->total_cents,
            'items' => OrderItemResource::collection($this->whenLoaded('items')),
        ];
    }
}
```
