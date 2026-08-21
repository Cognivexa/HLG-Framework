# Type System & Modern Syntax

## Strict Types

Add `declare(strict_types=1);` as the first statement in every new PHP file. Without it, PHP silently coerces scalar arguments (a string `"5"` passed where an `int` is expected becomes `5`), which hides bugs that only surface with unusual input.

## Readonly Properties & Constructor Promotion

```php
final class Point
{
    public function __construct(
        public readonly float $x,
        public readonly float $y,
    ) {}
}
```

Promoted, readonly properties remove the boilerplate of declaring a property, then assigning it in the constructor, then never allowing it to change — the three used to require three separate statements per property.

## Enums

Prefer backed enums over class-constant "enum" patterns for anything with a fixed, named set of values:

```php
enum OrderStatus: string
{
    case Pending = 'pending';
    case Paid = 'paid';
    case Shipped = 'shipped';

    public function isTerminal(): bool
    {
        return $this === self::Shipped;
    }
}
```

Enums can implement interfaces and carry methods, so validation logic that used to live in a separate switch statement can move onto the enum itself.

## Union & Intersection Types

```php
function formatId(int|string $id): string { /* ... */ }

function process(Countable&Iterator $collection): void { /* ... */ }
```

Reach for a union type when a parameter genuinely accepts more than one shape; reach for `null`-able types (`?Foo`) rather than a union with `null` scattered elsewhere, for readability.

## First-Class Callable Syntax

```php
$strlen = strlen(...);
array_map($strlen, $words);
```

This replaces the older `'strlen'` string-callable and `[$this, 'method']` array-callable forms, and is checked by static analysis the way a real reference is.
