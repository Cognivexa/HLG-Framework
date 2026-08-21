---
name: asset-namer
description: Renames and sorts a messy folder of design exports into a consistent convention (project-type-variant-size-version) and rebuilds folder structure by asset type.
argument-hint: [source-folder]
---

# Asset Namer

Turns a chaotic export dump into a predictable, searchable asset library in one pass.

## Input

$ARGUMENTS

## How It Works

1. Scan the source folder and detect file type, dimensions, and existing naming hints.
2. Infer project, variant, and version tokens from filenames and parent folders.
3. Apply the naming pattern to generate a collision-free filename per asset.
4. Move files into type-based subfolders such as icons, banners, and photos.
5. Log a rename manifest mapping old paths to new ones for safe rollback.