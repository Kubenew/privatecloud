name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Add dry-run mode for backup restore operations.

## Motivation
Users want to preview what a restore would do before actually applying changes.

## Proposed Solution
```bash
privatecloud backup restore <backup> --dry-run
```

This would:
- Extract backup to temporary location
- Run `kubectl diff -f` for each resource
- Show what would be created/modified/deleted
- Clean up without applying changes

## Alternatives Considered
- Verbose mode with detailed output
- JSON export of planned changes

## Additional Context
Aligns with existing `--dry-run` pattern in install/destroy commands.