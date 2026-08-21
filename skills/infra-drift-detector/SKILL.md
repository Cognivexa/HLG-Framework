---
name: infra-drift-detector
description: Compares a Terraform or Pulumi state file against the live cloud provider API to surface unmanaged changes, then generates a remediation plan to reconcile or import them.
argument-hint: [terraform-state-path]
---

# Infra Drift Detector

Finds the manual console changes nobody told the pipeline about, before they cause the next 2am incident.

## Input

$ARGUMENTS

## How It Works

1. Load the declared state file and enumerate every tracked resource and its expected attributes
2. Query the live cloud provider API for the current attributes of each tracked resource
3. Diff declared versus live state and classify each mismatch as drift, deletion, or orphan
4. Rank findings by blast radius, weighting production tags and public-facing resources highest
5. Generate terraform import or apply commands to bring state back into sync