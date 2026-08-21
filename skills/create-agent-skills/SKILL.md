---
name: create-agent-skills
description: Provides rigorous guidance for structuring and refining Claude Agent Skills, covering SKILL.md authoring, writing accurate when-to-trigger descriptions, and keeping a skill's scope narrow.
argument-hint: [skill-name]
---

# Create Agent Skills

Turns a skill idea into a SKILL.md that actually triggers when it should instead of one that gets skipped or fires on everything.

## Input

$ARGUMENTS

## How It Works

1. Define the single problem the skill solves and write it as a clear one-sentence description.
2. Draft trigger conditions specific enough to fire on relevant requests without matching unrelated ones.
3. Structure the SKILL.md body into scannable sections that a model can follow step by step mid-task.
4. Remove instructions that duplicate general model knowledge and keep only what is specific to this skill.
5. Review the finished skill against edge cases to confirm it neither over-triggers nor under-triggers.