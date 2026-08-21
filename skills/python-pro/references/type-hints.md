# Type Hints & Modern Syntax

## Generics

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    return items[0] if items else None
```

Use built-in generics (`list[T]`, `dict[K, V]`) rather than `typing.List`/`typing.Dict` — they've been the standard since Python 3.9 and read closer to the runtime type.

## Protocols (Structural Typing)

```python
from typing import Protocol

class SupportsTotal(Protocol):
    def total(self) -> int: ...

def print_total(item: SupportsTotal) -> None:
    print(item.total())
```

A Protocol lets a function accept "anything with a `.total()` method" without requiring a shared base class — useful for decoupling code from a specific inheritance hierarchy.

## Dataclasses vs. TypedDict vs. Pydantic

Use a `dataclass` for an internal, in-process value object with behavior. Use `TypedDict` for a plain dict shape you don't own the construction of (e.g. matching an external JSON structure) without runtime validation. Use Pydantic when the data crosses a trust boundary (an API request body, a config file) and needs actual runtime validation, not just a type hint that erases at runtime.

## Slots

Add `slots=True` to dataclasses that will be created in bulk — it removes the per-instance `__dict__`, cutting memory and speeding up attribute access, at the cost of not being able to add arbitrary attributes later.
