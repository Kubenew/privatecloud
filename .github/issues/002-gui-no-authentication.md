name: Bug report
about: Create a report to help us improve
title: '['
labels: bug, security
---

**Description**  
The web dashboard binds to `0.0.0.0:5000` by default and has no login. Anyone who can reach the host on port 5000 can view cluster status and, more critically, **destroy the entire cluster** via the GUI button.

**Steps to reproduce**  
1. Run `privatecloud gui` on a server with a public IP.
2. Access `http://<server-ip>:5000` from any machine.
3. Click "Destroy Entire Cluster" – no password required.

**Expected behaviour**  
- Default bind to `127.0.0.1` (safe for local use).
- Optional `--auth` flag to enable basic auth (username/password from env vars).
- Or require a pre‑shared token passed in the URL.

**Suggested fix**  
Change default host to `127.0.0.1`. Add `--auth` flag that reads `PRIVATECLOUD_GUI_USER` and `PRIVATECLOUD_GUI_PASS` environment variables.

**Environment**  
privatecloud v0.3.0