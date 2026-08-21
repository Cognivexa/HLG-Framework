---
name: test-driven-development
description: Enforces a strict red-green-refactor cycle by requiring a failing test before any implementation code, then only the minimum code needed to pass it, followed by refactoring.
argument-hint: [feature-or-fix]
---

# Test-Driven Development

Turns feature work into small proven increments instead of code written ahead of its tests.

## Input

$ARGUMENTS

## How It Works

1. Write a single test that captures the next small piece of desired behavior and confirm it fails.
2. Write the minimum implementation code needed to make that test pass, resisting any extra scope.
3. Run the full test suite to confirm the new test passes without breaking existing ones.
4. Refactor the implementation and test code for clarity while keeping all tests green.
5. Repeat the cycle for the next behavior until the feature or fix is complete.