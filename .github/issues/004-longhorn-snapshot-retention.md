name: Bug report
about: Create a report to help us improve
title: '['
labels: bug
---

**Description**  
Every `privatecloud backup create` creates new Longhorn snapshots for each volume. Over time, these accumulate and consume disk space. There is no automatic cleanup or retention policy.

**Steps to reproduce**  
Run `privatecloud backup create` 10 times. Check Longhorn UI – 10 snapshots per volume exist.

**Expected behaviour**  
User should be able to specify `--keep-last 5` or a cron‑based prune. Default could be to delete snapshots older than 7 days.

**Suggested fix**  
Add `--prune` flag that deletes snapshots older than N days. Or add a separate `privatecloud backup prune` command.

**Environment**  
privatecloud v0.3.0, Longhorn v1.6