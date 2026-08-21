---
name: social-crop-kit
description: Takes one source image and generates a full set of platform-ready crops (square, story, landscape, banner) using subject-aware framing so faces and focal points stay in frame.
argument-hint: [source-image]
---

# Social Crop Kit

One upload in, a full social media crop kit out, with nothing important cut off.

## Input

$ARGUMENTS

## How It Works

1. Load the source image and detect the primary subject or focal region.
2. Map the requested platforms to their required aspect ratios and dimensions.
3. Compute a crop window per ratio that keeps the focal region centered in frame.
4. Render each crop at the platform's native export resolution.
5. Package all variants into a labeled output folder ready for upload.