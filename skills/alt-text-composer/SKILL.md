---
name: alt-text-composer
description: Generates concise, screen-reader-friendly alt text for batches of images by describing subject, action, and context while stripping redundant phrasing like 'image of'.
argument-hint: [image-folder]
---

# Alt Text Composer

Makes an entire image library accessible without writing a single description by hand.

## Input

$ARGUMENTS

## How It Works

1. Scan the target folder and queue all supported image files.
2. Analyze each image for subject, setting, and notable action or embedded text.
3. Draft alt text under a configurable character limit, dropping filler phrases.
4. Flag purely decorative images for empty alt attributes instead of descriptions.
5. Write results to a CSV mapping filename to alt text for direct CMS import.