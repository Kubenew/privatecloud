name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Add scheduled backups via cron integration.

## Motivation
Manual backups are error-prone. Users need automated, regular backups with retention policies.

## Proposed Solution
```bash
privatecloud backup schedule --interval daily --keep 7
```

This would:
- Create a cron job or systemd timer
- Run `privatecloud backup create` at the specified interval
- Prune old backups based on retention policy
- Store schedule configuration in `privatecloud.yaml`

## Alternatives Considered
- Kubernetes CronJob-based backup operator
- External backup orchestration tools

## Additional Context
Complements the existing `privatecloud backup create` command.