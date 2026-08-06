"""A tiny calculator module used to demonstrate the Harness Engineering
Platform end to end. Contains two intentional problems for you to watch
Harness Engineering catch and Loop Engineering fix:

1. A hardcoded password (a security issue Harness's secret scanner and
   security scan both flag).
2. A bug in `subtract` — it adds instead of subtracting — which has a
   failing test in tests/test_calculator.py.
"""

DB_PASSWORD = "SuperSecret123!"


def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Return the difference of two integers."""
    return a + b  # bug: should be a - b
