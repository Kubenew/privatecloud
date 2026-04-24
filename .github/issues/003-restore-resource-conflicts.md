name: Bug report
about: Create a report to help us improve
title: '['
labels: bug
---

**Description**  
When restoring to an existing cluster (e.g., after a partial failure), `kubectl apply` may error if a resource already exists with conflicting fields, or if a namespace is in `Terminating` state. The restore operation then stops.

**Steps to reproduce**  
1. Deploy a workload via `privatecloud install`.
2. Delete only a specific deployment manually.
3. Run `privatecloud backup restore <backup>` – the restore might hang or error.

**Expected behaviour**  
Restore should have an option to forcibly replace existing resources (`--overwrite` or `--force`). Also, it should skip or retry on transient errors.

**Suggested fix**  
- Use `kubectl replace --force -f` instead of `apply` when `--overwrite` is given.
- Implement retry logic with exponential backoff.

**Environment**  
privatecloud v0.3.0, kubectl v1.32