---
name: proposal-pricing-table-generator
description: Build a pricing or tiering table for a sales proposal from a rate card and the deal's specific terms.
argument-hint: [rate-card] [deal-terms]
---

# Proposal Pricing Table Generator

Generate a pricing table that matches the deal terms exactly, not a generic template.

## Input

$ARGUMENTS

## How It Works

1. Load the base rate card and the deal-specific terms
2. Apply any negotiated discounts or volume tiers
3. Structure the table to match the format the buyer requested
4. Flag any pricing that falls outside standard discount policy
5. Include a plain-language summary line above the table