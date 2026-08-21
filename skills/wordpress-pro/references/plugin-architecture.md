# Plugin Architecture

## Main Plugin File Header

Every plugin needs a main file with a standard header comment block; WordPress parses this to populate the Plugins screen:

```php
<?php
/**
 * Plugin Name: My Plugin
 * Description: What the plugin does, in one sentence.
 * Version: 1.0.0
 * Requires at least: 6.4
 * Requires PHP: 8.1
 * Author: Your Name
 * License: GPL v2 or later
 * Text Domain: my-plugin
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // Disallow direct access.
}
```

## Structure

Keep the main file thin — it should only bootstrap. Put logic in `includes/`, admin-only code in `admin/`, and public-facing code in `public/`, each loaded conditionally with `is_admin()` so admin classes never load on the front end.

## Activation, Deactivation, Uninstall

```php
register_activation_hook( __FILE__, 'my_plugin_activate' );
register_deactivation_hook( __FILE__, 'my_plugin_deactivate' );

function my_plugin_activate(): void {
    // Create tables, set default options, flush rewrite rules.
    flush_rewrite_rules();
}

function my_plugin_deactivate(): void {
    // Clear scheduled events, flush rewrite rules. Do NOT delete user data here.
    flush_rewrite_rules();
}
```

Data deletion belongs in `uninstall.php` at the plugin root (WordPress runs this file, not a hook, when a user clicks Delete):

```php
<?php
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
    exit;
}
delete_option( 'my_plugin_settings' );
```

## Settings API

```php
add_action( 'admin_init', function () {
    register_setting( 'my_plugin_group', 'my_plugin_settings', [
        'sanitize_callback' => 'my_plugin_sanitize_settings',
    ] );

    add_settings_section( 'main', 'Main Settings', '__return_false', 'my-plugin' );

    add_settings_field( 'api_key', 'API Key', function () {
        $value = get_option( 'my_plugin_settings' )['api_key'] ?? '';
        echo '<input type="text" name="my_plugin_settings[api_key]" value="' . esc_attr( $value ) . '" />';
    }, 'my-plugin', 'main' );
} );
```

## Updates

For plugins outside the WordPress.org repository, ship a self-hosted update check using the `update_{type}_{file}` transient filters, or vendor a maintained update-checker library. Always version-gate breaking changes and provide a migration routine keyed off a stored `my_plugin_db_version` option, run on `plugins_loaded`.
