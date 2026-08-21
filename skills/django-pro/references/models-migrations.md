# Models & Migrations

## Relationships & Managers

Choose the relationship field that matches the real cardinality (`ForeignKey`, `ManyToManyField`, `OneToOneField`), and add a custom `Manager` for a query pattern used in more than one place (`Article.published.all()`) rather than repeating the filter everywhere it's needed.

## Migrations

Run `makemigrations` and commit the generated file — never hand-edit a migration's operations list, since Django's migration graph depends on the recorded dependency chain matching what actually ran. Run `makemigrations --check --dry-run` in CI to catch model changes that don't have a corresponding migration.

## Safe Schema Changes on Live Tables

Adding a `NOT NULL` field to a populated table needs a default or a two-step migration (add nullable, backfill, then make non-nullable) — Django will prompt for a one-off default interactively, but that default doesn't get recorded for future rows unless it's also set in the model.

## QuerySets Are Lazy

A queryset doesn't hit the database until it's iterated, sliced with a concrete index, or coerced (`list()`, `len()`, boolean check). Chain filters freely before that point; each additional `.filter()` after evaluation triggers a new query instead of refining the cached one.
