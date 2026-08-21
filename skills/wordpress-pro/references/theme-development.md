# Theme Development

## Template Hierarchy

WordPress resolves the template for a request by walking a fixed hierarchy, from most specific to least specific. For a single post it checks, in order: `single-{post-type}-{slug}.php`, `single-{post-type}.php`, `single.php`, `singular.php`, `index.php`. Build the most specific template only when that page genuinely needs different markup; otherwise let it fall through so one template serves many URLs.

## Child Themes

Never edit a parent theme directly — changes are lost on update. Create a child theme instead:

```
/* style.css */
/*
 Theme Name: My Theme Child
 Template: my-theme
 Version: 1.0.0
*/
```

```php
// functions.php — enqueue the parent stylesheet, then the child's
add_action( 'wp_enqueue_scripts', function () {
    wp_enqueue_style( 'parent-style', get_template_directory_uri() . '/style.css' );
    wp_enqueue_style(
        'child-style',
        get_stylesheet_uri(),
        [ 'parent-style' ],
        wp_get_theme()->get( 'Version' )
    );
} );
```

## Full Site Editing (FSE) / Block Themes

A block theme replaces `header.php`/`footer.php`/`sidebar.php` with a `theme.json` design-token file and HTML template parts:

```
my-block-theme/
├── theme.json
├── templates/
│   ├── index.html
│   └── single.html
└── parts/
    ├── header.html
    └── footer.html
```

`theme.json` controls global styles, color palettes, typography presets, and layout settings that the block editor reads directly — set `settings.color.palette` and `styles.typography` there rather than in a stylesheet so the editor UI and the front end stay in sync.

Templates and template parts are just block markup (`<!-- wp:group -->` etc.) saved as `.html` files; edit them visually in Appearance → Editor or hand-author the block comments directly.

## Theme Support

Declare theme features in `functions.php` via `add_theme_support()`: `title-tag`, `post-thumbnails`, `html5`, `custom-logo`, `editor-styles`, and `align-wide` are the ones nearly every theme needs. Register nav menus with `register_nav_menus()` and image sizes with `add_image_size()` in the same `after_setup_theme` hook.
