name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Support external etcd backups for k3s clusters with external databases.

## Motivation
Clusters using external etcd (PostgreSQL, etcd) need their database backed up to ensure full state recovery.

## Proposed Solution
When `privatecloud backup create` detects external etcd configuration:
1. Trigger etcd snapshot
2. Include snapshot in backup tarball
3. Verify snapshot integrity

For k3s with external PostgreSQL:
```bash
pg_dump -h $PG_HOST -U $PG_USER -d k3s > k3s-db.sql
```

## Alternatives Considered
- Velero with etcd plugin
- Separate backup operator

## Additional Context
Relevant for HA deployments with external database.