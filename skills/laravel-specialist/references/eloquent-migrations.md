# Eloquent & Migrations

## Relationships

Declare the relationship type that matches the actual cardinality — `hasMany`/`belongsTo` for one-to-many, `belongsToMany` for many-to-many with a pivot table, `hasManyThrough` when a relationship spans an intermediate model. Getting this wrong is the root cause of most N+1 and incorrect-query bugs.

```php
class Order extends Model
{
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }
}
```

## Migrations

Write every schema change as a migration, and make it reversible with a real `down()`:

```php
public function up(): void
{
    Schema::table('orders', function (Blueprint $table) {
        $table->unsignedInteger('total_cents')->nullable()->after('total');
    });
}

public function down(): void
{
    Schema::table('orders', function (Blueprint $table) {
        $table->dropColumn('total_cents');
    });
}
```

For a column with live production traffic reading it, add it nullable first, backfill in a separate deploy, then make it non-nullable in a third — never add a NOT NULL column with no default to a populated table in one step.

## Seeders & Factories

Define a model factory for every model used in tests, with realistic-but-fake defaults via Faker, and states for common variations:

```php
class OrderFactory extends Factory
{
    public function definition(): array
    {
        return ['status' => 'pending', 'total_cents' => $this->faker->numberBetween(500, 50000)];
    }

    public function paid(): static
    {
        return $this->state(['status' => 'paid']);
    }
}
```
