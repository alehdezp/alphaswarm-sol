# Testing Philosophy Summary

This is a short, testing-only summary. The canonical source is ` .planning/testing/rules/canonical/TESTING-PHILOSOPHY.md `.

## Why Real Testing Is Mandatory

- The product is a CLI workflow, so human-like interaction must be validated.
- Simulations miss timing, prompts, and real error behavior.
- Evidence-first validation requires real transcripts and timing.

## Core Principles

- LIVE execution only for validation.
- External ground truth only.
- Evidence-first with real graph node IDs and file:line locations.
- Imperfection expected; perfect metrics are a red flag.

