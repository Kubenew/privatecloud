name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Auto-backup Terraform state before destroy operations.

## Motivation
Even when destroy is called without an explicit backup, users should be able to recover from accidental destruction.

## Proposed Solution
When `privatecloud destroy` is called:
1. Automatically save Terraform state to `backups/destroy-pre-<timestamp>/`
2. Keep last N pre-destroy backups (configurable, default 3)
3. Add `--no-auto-backup` flag to disable

This allows `privatecloud restore` to recover Terraform state if needed.

## Alternatives Considered
- Prompt user to confirm backup before destroy
- Immutable infrastructure approach (no destroy possible)

## Additional Context
Complements existing `--backup` flag on destroy command.