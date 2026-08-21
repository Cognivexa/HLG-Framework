---
name: security-questionnaire-responder
description: Drafts answers to vendor security questionnaires and SOC 2/ISO 27001 audit requests by pulling evidence from your existing policy docs, architecture diagrams, and control matrices.
argument-hint: [questionnaire-file]
---

# Security Questionnaire Responder

Turns a 200-question vendor security review from a week of scrambling into an afternoon of review.

## Input

$ARGUMENTS

## How It Works

1. Parse the incoming questionnaire into individual control and policy questions
2. Match each question against your indexed policy documents and control matrix
3. Draft an evidence-backed answer with citations to the source document and section
4. Flag unanswerable questions where no matching control or evidence exists yet
5. Compile the final response into the questionnaire's original format for submission