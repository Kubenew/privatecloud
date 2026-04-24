name: Feature request
about: Suggest a new feature for PrivateCloud
title: '['
labels: enhancement, backup
---

## Feature Description
Add backup encryption to `privatecloud backup create` with `--encrypt` flag.

## Motivation
Backups may contain database passwords, TLS keys, cloud credentials. Currently secrets are stored in plaintext in backup tarballs.

## Proposed Solution
- Add `--encrypt` flag that uses a password/passphrase or a public key.
- Integrate with [age](https://github.com/FiloSottile/age) (pure Python or subprocess) or use `openssl enc -aes-256-cbc`.
- Store encryption key in privatecloud.yaml or prompt each time.

## Alternatives Considered
- Mozilla SOPS integration
- GPG encryption
- Kubernetes secrets encryption at rest

## Additional Context
Related to issue #001 (Backup stores secrets in plaintext)

## Labels
enhancement, security, backup