---
name: writing-skills
description: Invoked when authoring a new Claude skill, editing an existing one, or auditing one before deployment, this skill checks the SKILL.md front matter, trigger description, and scope boundaries against common authoring mistakes. It flags vague triggers, missing metadata, and scope creep before the skill ships.
argument-hint: [skill-directory]
---

# Writing Skills

Catches a badly triggered or bloated skill before it ships, instead of after it misfires in production.

## Input

$ARGUMENTS

## How It Works

1. Parse the SKILL.md front matter and confirm required fields are present and correctly formatted.
2. Evaluate the trigger description for specificity, flagging wording too vague to reliably fire.
3. Check the skill's stated scope against its actual instructions for mismatches or creep.
4. Compare structure and tone against known good skills to catch inconsistent conventions.
5. Produce a list of concrete fixes ranked by how likely each is to cause a misfire.