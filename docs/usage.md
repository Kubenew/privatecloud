# PrivateCloud v0.7.0 - Usage Guide

## Installation

```bash
pip install privatecloud==0.7.0
```

---

## Quickstart

```bash
# 1. Initialize
privatecloud init

# 2. Verify
privatecloud doctor --diagnostics

# 3. Deploy
privatecloud install-cluster

# 4. Dashboard
privatecloud gui --port 8080 --auth
```

---

## Cluster Management

### Upgrade
```bash
privatecloud upgrade v1.30.0+k3s1 --dry-run
privatecloud upgrade v1.30.0+k3s1 --backup
```

### High Availability
```bash
privatecloud ha status
privatecloud ha setup --masters IP1,IP2,IP3 --workers IP4,IP5
```

### Multi-Cluster
```bash
privatecloud cluster list/add/switch/remove
```

---

## Backup & Recovery

### Basic
```bash
privatecloud backup create
privatecloud backup create --encrypt
privatecloud backup create --s3 my-bucket
```

### Schedule
```bash
privatecloud backup schedule daily --keep 7
```

### Restore
```bash
privatecloud backup restore <name> --force
```

### Point-in-Time
```bash
privatecloud snapshot <volume>
privatecloud restore <volume> <snapshot>
privatecloud snapshots-list
```

---

## Add-ons

```bash
privatecloud addon list/install/uninstall/search
```

---

## Configuration

```bash
privatecloud lint
privatecloud plan
```

---

## Complete CLI Reference

| Command | Description |
|---------|-------------|
| `init` | Generate config |
| `doctor` | Check deps |
| `plan` | Preview config |
| `install-cluster` | Deploy |
| `upgrade` | Upgrade K8s |
| `ha` | HA management |
| `backup` | Backup ops |
| `snapshot` | PITR |
| `cluster` | Multi-cluster |
| `addon` | Marketplace |
| `gui` | Web UI |
| `lint` | Validate |