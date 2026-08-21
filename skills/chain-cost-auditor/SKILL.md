---
name: chain-cost-auditor
description: Walks a multi-step prompt chain and computes token usage and dollar cost per step, then flags the highest-cost hops for compression or caching.
argument-hint: [chain-config.json]
---

# Chain Cost Auditor

Shows you exactly which link in your prompt chain is burning your budget.

## Input

$ARGUMENTS

## How It Works

1. Parse the chain config to identify each step's prompt and target model.
2. Tokenize inputs and outputs per step using that model's tokenizer.
3. Apply current per-model pricing to compute per-step and cumulative cost.
4. Rank steps by cost share and detect redundant or cacheable calls.
5. Output a cost breakdown table with concrete trimming suggestions.