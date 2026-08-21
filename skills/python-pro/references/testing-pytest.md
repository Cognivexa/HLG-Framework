# Testing with pytest

## Fixtures

A fixture separates setup from the assertion, and pytest resolves its dependency graph automatically:

```python
@pytest.fixture
def db_session():
    session = create_test_session()
    yield session
    session.rollback()
```

The code after `yield` runs as teardown, guaranteed even if the test fails.

## Parametrize

Replace near-duplicate test functions that only differ by input with one parametrized test:

```python
@pytest.mark.parametrize("value,expected", [(0, False), (1, True), (-1, True)])
def test_is_nonzero(value, expected):
    assert is_nonzero(value) is expected
```

## Mocking

Prefer dependency injection (pass the collaborator in) over patching a module attribute with `unittest.mock.patch` — patching couples the test to the exact import path of the dependency, which breaks silently on a refactor.

## Test Isolation

Each test should be able to run alone and in any order. A test that depends on state left behind by a previous test is a source of flaky CI runs; use fixtures with proper teardown (or `pytest-django`'s transaction-per-test) instead of shared mutable state.
