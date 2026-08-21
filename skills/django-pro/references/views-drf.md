# Views & DRF

## Class-Based Views

Prefer Django's generic class-based views (`ListView`, `DetailView`, `CreateView`) for standard CRUD over hand-writing the same query-render-response boilerplate in a function view. Override only the specific hook you need (`get_queryset`, `form_valid`) rather than the whole method.

## Serializers

A DRF `ModelSerializer` both validates input and shapes output — keep `fields` explicit rather than `"__all__"` so adding a sensitive model field later doesn't silently expose it through the API.

## Viewsets & Routers

```python
router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
```

A `ModelViewSet` plus a router gives the full CRUD URL set from one class — override `get_queryset` to scope results to the requesting user rather than trusting the default unfiltered queryset.

## Pagination

Set a default pagination class (`PageNumberPagination` or `CursorPagination`) project-wide in settings rather than per-view, so no endpoint accidentally returns an unbounded result set as the table grows.
