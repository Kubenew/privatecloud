# Changelog

Generated: 2026-04-24

---

## [0.7.0] - 2026-04-24

### Features

#### High Availability
- HA cluster status monitoring
- HA setup with multi-master configuration
- External database support (PostgreSQL, etcd, MySQL)
- Cluster health detection for HA mode

#### Point-in-Time Recovery
- Longhorn volume snapshot creation
- Volume restore from snapshots
- Snapshot listing and management
- PVC creation from snapshots

#### Release Management
- Changelog generation from git history
- Release notes generator
- Commit categorization (features, fixes, etc)

### Bug Fixes

### Security

### Documentation
- Complete README overhaul
- Command reference documentation
- Roadmap to v1.0

---

## [0.6.0] - 2026-04-24

### Features

#### Cluster Upgrade
- `privatecloud upgrade <version>` command
- Pre-upgrade backup and validation
- Dry-run mode for safe preview
- Node drain/uncordon support

#### Multi-Cluster Management
- `privatecloud cluster list/add/switch/remove`
- Per-cluster kubeconfig storage
- Quick switch between clusters

#### Add-on Marketplace
- `privatecloud addon list/install/uninstall/search`
- Pre-configured add-on registry
- Categories: monitoring, logging, security, networking

#### Configuration Linting
- `privatecloud lint` command
- YAML syntax validation
- Secret detection and warnings

---

## [0.5.0] - 2026-04-24

### Features

#### Cloud Storage Integration
- S3 upload/download (boto3 or AWS CLI fallback)
- GCS upload/download
- Azure Blob upload/download
- Unified backup listing

#### GUI Metrics Dashboard
- Cluster metrics endpoint
- Node/Pod status monitoring
- Longhorn volume health
- Real-time refresh

#### Scheduled Backups
- `privatecloud backup schedule <interval>`
- Cron and systemd timer support
- Retention policy (--keep)

#### etcd Backup
- k3s etcd-snapshot save/restore
- Automatic etcd detection
- Backup integration

---

## [0.4.0] - 2026-04-24

### Features

#### Security Hardening
- Backup encryption with age
- GUI authentication (--auth flag)
- Auto-backup Terraform state before destroy
- Login page for GUI

#### Backup Enhancements
- Longhorn snapshot pruning (--keep-last)
- Restore with --force flag
- Backup verification
- Restore dry-run mode

#### Enhanced Diagnostics
- kubectl connection check
- Helm/Terraform version checks
- Certificate expiry warnings
- Longhorn health check

---

## [0.3.0] - 2026-04-24

### Features

#### Web GUI Dashboard
- `privatecloud gui --port 8080`
- Cluster health status
- One-click backup/restore/destroy

#### Backup & Restore
- Full cluster state backup
- `privatecloud backup create/list/restore/delete`

#### Security
- Auto-generated .gitignore
- Secret masking in logs
- Environment variable support (${VAR})

#### Enhanced Destroy
- --yes, --dry-run, --backup flags
- Auto-backup before destruction

---

## [0.2.1] - 2026-04-24

### Features
- Provider abstraction (bare-metal, Proxmox)
- Terraform runner
- Helm-based service installation
- Basic CLI commands (init, doctor, plan, install, destroy)