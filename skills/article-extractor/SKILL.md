---
name: article-extractor
description: Extracts clean article content from a URL such as a blog post, news article, or tutorial, stripping ads, navigation, and other boilerplate. It saves the resulting readable text for downstream use such as summarizing or archiving.
argument-hint: [article-url]
---

# Article Extractor

Pulls out the actual article, instead of the ads and navigation wrapped around it.

## Input

$ARGUMENTS

## How It Works

1. Fetch the raw HTML from the given URL.
2. Identify the main content block by filtering out navigation, ads, and sidebar elements.
3. Preserve heading structure, lists, and inline links within the extracted content.
4. Clean up leftover boilerplate such as newsletter prompts and share buttons.
5. Save the resulting readable text to a file for downstream use.