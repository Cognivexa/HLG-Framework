---
name: image-enhancer
description: Improves the visual quality of images, especially screenshots, by upscaling resolution, sharpening blurred detail, and reducing compression artifacts such as banding and blockiness.
argument-hint: [image-file]
---

# Image Enhancer

Turns a blurry, compressed screenshot into something worth pasting into a document.

## Input

$ARGUMENTS

## How It Works

1. Inspect the source image to identify its resolution, format, and dominant quality issues.
2. Upscale the image using an interpolation method suited to its content, such as edge-aware scaling for text or UI screenshots.
3. Sharpen fine detail without amplifying existing noise or artifacts.
4. Reduce compression artifacts like blocking and color banding introduced by lossy formats.
5. Export the result at a specified resolution and format, comparing it side by side with the original on request.