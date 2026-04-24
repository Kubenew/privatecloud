name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Add support for backing up to cloud object storage (S3, GCS, Azure Blob).

## Motivation
Local backups are vulnerable to disk failures. Cloud storage provides durability, redundancy, and offsite disaster recovery.

## Proposed Solution
```bash
privatecloud backup create --s3-bucket my-bucket/backups
privatecloud backup create --gcs-bucket my-project/backups
privatecloud backup create --azure-container my-container/backups
```

Requirements:
- AWS/GCP/Azure credentials via environment variables or config
- Upload tarball after creation
- Optional: download on restore

## Alternatives Considered
- Restic or Borg backup integration
- Velero integration for Kubernetes-native backups

## Additional Context
Should work alongside local backups (local-first, cloud-sync option).