---
name: deal-desk-checklist
description: Review a proposed deal against discount and approval policy before it goes to signature.
argument-hint: [deal-summary]
---

# Deal Desk Checklist

Catch policy violations before the deal reaches signature, not after.

## Input

$ARGUMENTS

## How It Works

1. Load the deal summary and the current approval policy thresholds
2. Check discount level against the approval matrix
3. Flag non-standard terms that need legal or finance sign-off
4. Verify required approvals are attached, not just requested
5. Report a clear pass/fail with the specific policy citation for any flag