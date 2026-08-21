# Authentication & Permissions

## Django Auth

Use Django's built-in `User` model (or a custom user model set up before the first migration — swapping it later is painful) and its password hashers (PBKDF2/Argon2 by default) rather than a hand-rolled auth system.

## DRF Permission Classes

`IsAuthenticated` only checks that a request is logged in — it says nothing about whether that user may access *this specific* object. Add object-level permission checks (`has_object_permission`) for any endpoint that takes a resource ID:

```python
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
```

## Combining Permissions

```python
permission_classes = [IsAuthenticated, IsOwner | IsAdminUser]
```

DRF supports `&`/`|`/`~` composition of permission classes — use it instead of writing one large permission class with branching logic for every role combination.

## Token vs. Session Auth

Use session auth for a same-origin, cookie-based frontend, and token auth (DRF's TokenAuthentication, or JWT via a library) for a separate SPA or mobile client. Don't mix both as the primary mechanism for the same endpoint without a specific reason — it doubles the surface area to secure.
