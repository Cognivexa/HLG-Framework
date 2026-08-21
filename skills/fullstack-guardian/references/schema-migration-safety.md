# Schema Migration Safety

## Expand/Contract

Never rename or drop a column in the same deploy that stops using it. Split any breaking schema change into:

1. **Expand** — add the new column/table alongside the old one.
2. **Migrate** — backfill and switch application code to the new shape, deployed separately.
3. **Contract** — once no code path reads the old column, drop it in a later deploy.

## Rolling Deploys

During a rolling deploy, old and new application code run simultaneously against the same database for some window. A migration is only safe if both the old code and the new code can operate correctly against the schema at every point in that window — check this explicitly, don't assume it.

## Default Values on Large Tables

Adding a `NOT NULL` column with no default to a large, actively-written table can lock it for the duration of the backfill on some databases. Add the column nullable, backfill in batches, then add the `NOT NULL` constraint once every row has a value.

## Index Changes

Adding an index on a large table can hold a lock depending on the database; use the database's online/concurrent index-creation mechanism (e.g. `CREATE INDEX CONCURRENTLY` in Postgres) rather than a blocking default index build during business hours.
