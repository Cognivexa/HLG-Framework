# Performance & Security

## Caching

Use transients for expensive, infrequently-changing data (API responses, computed report data):

```php
$data = get_transient( 'my_plugin_report' );
if ( false === $data ) {
    $data = my_plugin_expensive_calculation();
    set_transient( 'my_plugin_report', $data, HOUR_IN_SECONDS );
}
```

On a host with a persistent object cache (Redis/Memcached), transients are automatically backed by it; without one, they fall back to the `wp_options` table, so keep values small and TTLs reasonable to avoid table bloat.

## Query Optimization

- Avoid `meta_query` on unindexed meta keys at scale; register the value as a real column or a taxonomy term when it drives a frequent query.
- Set `'no_found_rows' => true` on `WP_Query` when you don't render pagination — it skips a `SQL_CALC_FOUND_ROWS` count query.
- Set `'update_post_meta_cache' => false` and `'update_post_term_cache' => false` when a loop only needs post titles/IDs.
- Prefer `WP_Query`/`$wpdb->prepare()` over raw `$wpdb->query()` string concatenation for anything touching user input.

## Security Hardening Checklist

- Disable the theme/plugin file editor: `define( 'DISALLOW_FILE_EDIT', true );` in `wp-config.php`.
- Remove the generator meta tag (`remove_action( 'wp_head', 'wp_generator' )`) so the WordPress version isn't advertised.
- Rate-limit or gate `wp-login.php` (fail2ban, a login-attempt limiter, or moving auth behind an app-level check) — brute force is the most common WordPress compromise vector.
- Validate and restrict file uploads by MIME type and extension; never trust the client-supplied `Content-Type`.
- Set restrictive file permissions (`644` files, `755` directories) and keep `wp-config.php` outside the web root when the host allows it.
- Keep core, themes, and plugins patched — most real-world WordPress compromises exploit a known, already-fixed vulnerability in outdated code.

## Backups

Back up the database and the `wp-content` uploads/themes/plugins separately, on a schedule matched to how often content changes, and verify restores periodically — an untested backup is not a backup.
