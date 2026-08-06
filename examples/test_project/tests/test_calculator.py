"""Tests for calculator.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calculator import add, subtract


def test_add():
    """add() returns the correct sum."""
    assert add(2, 3) == 5


def test_subtract():
    """subtract() returns the correct difference."""
    assert subtract(5, 2) == 3
