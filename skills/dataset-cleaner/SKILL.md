---
name: dataset-cleaner
description: Clean a messy dataset: standardize types, handle missing values deliberately, and log every transformation applied.
argument-hint: [dataset-file]
---

# Dataset Cleaner

Every cleaning decision is logged, so the cleaned dataset stays auditable.

## Input

$ARGUMENTS

## How It Works

1. Profile column types, missing rates, and outliers before touching anything
2. Standardize types and formats consistently across columns
3. Choose an explicit, documented strategy for missing values per column
4. Log every transformation applied, in order, to a changelog
5. Re-profile the cleaned dataset and report what changed