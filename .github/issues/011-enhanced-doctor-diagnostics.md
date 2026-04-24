name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement
---

## Feature Description
Enhance `privatecloud doctor` with comprehensive diagnostics.

## Motivation
Users need actionable diagnostics to troubleshoot issues before they escalate.

## Proposed Solution
Expand `privatecloud doctor` to check:
- Network connectivity to cluster nodes
- API token validity (Proxmox, cloud providers)
- Terraform version and provider plugins
- Helm repo status and chart versions
- Disk space on nodes
- k3s service status
- Certificate expiry warnings

Output "✅ Healthy" or show actionable error messages with suggested fixes.

## Alternatives Considered
- Separate `privatecloud diagnose` command
- JSON output for automation

## Additional Context
Would improve user experience and reduce support burden.