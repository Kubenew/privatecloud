name: Bug report
about: Create a report to help us improve
title: '['
labels: bug
---

**Description**  
When running `privatecloud backup create`, the tool exports all Kubernetes secrets as plain YAML inside the backup tarball. This poses a security risk if backups are stored on shared or untrusted storage.

**Steps to reproduce**  
1. Create a secret: `kubectl create secret generic db-pass --from-literal=password=mysecret`
2. Run `privatecloud backup create`
3. Extract the backup tarball and inspect `namespaces/default/secrets.yaml`

**Expected behaviour**  
Secrets should be encrypted by default (e.g., with age, GPG, or AES), or the user should be warned and given an `--encrypt` flag.

**Suggested fix**  
- Add `--encrypt` flag that uses a password/passphrase or a public key.
- Optionally integrate with Mozilla SOPS.

**Environment**  
privatecloud v0.3.0, kubectl v1.32