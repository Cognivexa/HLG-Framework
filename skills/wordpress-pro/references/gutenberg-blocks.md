# Gutenberg Blocks

## block.json

Every block starts with a manifest that declares its identity, attributes, and supports:

```json
{
  "apiVersion": 3,
  "name": "my-plugin/testimonial",
  "title": "Testimonial",
  "category": "widgets",
  "icon": "format-quote",
  "attributes": {
    "quote": { "type": "string", "source": "html", "selector": "blockquote" },
    "author": { "type": "string" }
  },
  "supports": { "align": [ "wide", "full" ] },
  "editorScript": "file:./index.js",
  "style": "file:./style-index.css"
}
```

## Registering the Block (server-side)

```php
add_action( 'init', function () {
    register_block_type( __DIR__ . '/build/testimonial' );
} );
```

## Static vs. Dynamic Blocks

A static block saves its markup directly into post content. A dynamic block instead renders server-side on every request — use this whenever the output depends on data that can change independently of the post (latest posts, live pricing, user-specific content). Add a `render_callback` (or a `render.php` file referenced from `block.json` as `"render": "file:./render.php"`) and leave the block's `save` function returning `null`.

```php
function my_plugin_render_testimonial( array $attributes ): string {
    return sprintf(
        '<blockquote>%s <cite>%s</cite></blockquote>',
        wp_kses_post( $attributes['quote'] ?? '' ),
        esc_html( $attributes['author'] ?? '' )
    );
}
```

## InnerBlocks

Container blocks that accept nested content use `<InnerBlocks />` in the edit component and `InnerBlocks.Content` in save, optionally with `allowedBlocks` to restrict what can be nested and `template` to pre-populate a default layout.

## Block Patterns

Register a reusable multi-block layout as a pattern so it's insertable but not locked to a single block instance:

```php
register_block_pattern( 'my-plugin/cta-banner', [
    'title'      => __( 'Call to Action Banner', 'my-plugin' ),
    'categories' => [ 'call-to-action' ],
    'content'    => file_get_contents( __DIR__ . '/patterns/cta-banner.html' ),
] );
```

## Full Site Editing Interplay

Dynamic blocks and patterns both work inside block-theme templates the same way they work in post content, since FSE templates are themselves just block markup.
