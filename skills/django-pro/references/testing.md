# Testing

## pytest-django

Prefer pytest-django's fixtures (`client`, `db`) and plain `assert` statements over Django's `TestCase`/`unittest`-style assertions for new test suites — they read more directly and integrate with the wider pytest ecosystem (parametrize, plugins).

```python
def test_order_list_requires_auth(client):
    response = client.get("/api/orders/")
    assert response.status_code == 401
```

## Factories

Use `factory_boy` to build test data instead of hand-constructing model instances in every test:

```python
class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order
    status = "pending"
    total_cents = factory.Faker("random_int", min=500, max=50000)
```

## Database Access in Tests

Mark any test that touches the database with `@pytest.mark.django_db` (or use the `db` fixture) — pytest-django wraps each such test in a transaction that rolls back afterward, so tests stay isolated without manual cleanup.

## Testing the Admin and Management Commands

Don't skip coverage for Django admin customizations or management commands just because they're "just tooling" — a broken `import_data` management command that silently corrupts records in production is exactly the kind of bug a quick test would catch.
