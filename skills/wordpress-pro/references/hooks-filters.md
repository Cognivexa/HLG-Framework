# Hooks & Filters

## Actions vs. Filters

An action runs code at a point in the request lifecycle and does not return a value: `do_action( 'my_event', $arg )` / `add_action( 'my_event', $callback, $priority, $accepted_args )`. A filter transforms a value and must return it: `apply_filters( 'my_value', $value, $arg )` / `add_filter( 'my_value', $callback )` — a filter callback that forgets to `return` silently breaks the value for every subscriber after it.

## Priority & Accepted Args

```php
add_action( 'save_post', 'my_plugin_on_save', 20, 2 ); // priority 20, expects 2 args
function my_plugin_on_save( int $post_id, WP_Post $post ): void {
    if ( wp_is_post_revision( $post_id ) ) {
        return;
    }
    // ...
}
```

Lower priority numbers run earlier (default is 10). Bump priority up to run after other integrations have had a chance to act, or down to run first and let others build on your change.

## Custom Hooks

Fire your own hooks around meaningful extension points so other plugins and child themes can integrate without patching your code:

```php
do_action( 'my_plugin_before_render', $context );
$output = apply_filters( 'my_plugin_output_html', $output, $context );
```

Document every custom hook's parameters in a docblock above the `do_action`/`apply_filters` call — that comment is the only reference other developers get.

## Common Pitfalls

- A callback registered as a closure or a class method can only be removed with `remove_action`/`remove_filter` if you kept a reference to the exact same callable — an anonymous closure registered elsewhere can't be removed at all.
- Hooking too late (e.g. on `wp_footer` instead of `wp_enqueue_scripts`) causes enqueue calls to be ignored because WordPress has already printed the relevant tag.
- Removing a core hook you didn't add requires matching the exact priority it was originally registered with; `remove_action( 'hook', 'callback' )` without the priority argument fails silently if the original priority wasn't 10.
