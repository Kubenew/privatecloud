name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, gui
---

## Feature Description
Enhance GUI dashboard with Prometheus metrics visualization.

## Motivation
Users want visual insights into cluster health without leaving the dashboard.

## Proposed Solution
Show in the GUI:
- Node CPU/memory usage (from metrics API)
- Longhorn volume health and capacity
- Certificate expiry dates (from cert-manager)
- Pod resource usage
- Embedded Grafana iframe or simplified graphs

## Alternatives Considered
- Redirect to Grafana dashboard
- Separate metrics service

## Additional Context
Requires kube-prometheus-stack to be enabled in services.