name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, security
---

## Feature Description
Add authentication to the web GUI dashboard.

## Motivation
The web dashboard currently binds to `0.0.0.0:5000` with no login. Anyone who can reach the host can view cluster status and destroy the cluster.

## Proposed Solution
**Two modes:**
1. **Local mode** (`--bind 127.0.0.1`) – no auth, safe for local access
2. **Remote mode** (`--bind 0.0.0.0 + --auth`) – basic auth with configurable user/pass

Implementation:
- Change default host from `0.0.0.0` to `127.0.0.1`
- Add `--auth` flag that reads `PRIVATECLOUD_GUI_USER` and `PRIVATECLOUD_GUI_PASS` environment variables
- Use Flask-HTTPAuth or similar for basic auth

## Alternatives Considered
- Token-based auth (pre-shared key in URL)
- OAuth2/OIDC integration with existing identity providers

## Additional Context
Related to issue #002 (GUI lacks authentication)