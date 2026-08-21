---
name: deep-research
description: Performs autonomous multi-step research on a given topic by decomposing the question into sub-questions, gathering sources for each, and synthesizing the results into a cited report. It is suited to open-ended questions that require pulling together information from multiple independent sources.
argument-hint: [research-question]
---

# Deep Research

Runs an entire research pass end to end, instead of stopping after the first search result.

## Input

$ARGUMENTS

## How It Works

1. Break the research question down into a set of specific, answerable sub-questions.
2. Search for and gather sources addressing each sub-question independently.
3. Evaluate source credibility and discard low-quality or contradictory outliers.
4. Synthesize findings across sub-questions into a coherent narrative.
5. Compile a final report with inline citations linking each claim back to its source.