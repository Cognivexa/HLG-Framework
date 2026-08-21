# Composer & Autoloading

## PSR-4 Autoloading

```json
{
  "autoload": {
    "psr-4": {
      "App\\": "src/"
    }
  },
  "autoload-dev": {
    "psr-4": {
      "App\\Tests\\": "tests/"
    }
  }
}
```

The namespace prefix must map to the directory: `App\Billing\Invoice` resolves to `src/Billing/Invoice.php`. Run `composer dump-autoload -o` to regenerate an optimized classmap after adding new PSR-4 roots.

## Versioning Dependencies

Pin with a caret constraint (`^8.2`) to allow non-breaking updates, and commit `composer.lock` so every environment — including CI — installs the exact same resolved versions. Run `composer audit` regularly to catch dependencies with known CVEs.

## Private Packages

For internal packages not published to Packagist, add a VCS or path repository:

```json
{
  "repositories": [
    { "type": "vcs", "url": "git@github.com:my-org/internal-package.git" }
  ]
}
```

## Scripts & Platform Requirements

Declare the minimum PHP version and required extensions in `composer.json`'s `require` block (`"php": "^8.2"`, `"ext-pdo": "*"`) so `composer install` fails fast on an incompatible environment instead of failing at runtime.
