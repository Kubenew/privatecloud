# PrivateCloud

**PrivateCloud** is a Python CLI installer that provisions a Kubernetes-based private cloud stack.

It focuses on **fast deployment**, **repeatable infrastructure**, and **production-ready defaults**.

## v0.3.0 Release Notes

### New Features

**Web-based GUI Dashboard**
- Start with `privatecloud gui --port 8080`
- View cluster health (nodes, pods)
- One-click backup/restore
- Safe cluster destruction

**Backup & Restore**
- `privatecloud backup create` - Creates full backup to `backups/` directory
- `privatecloud backup list` - Lists all available backups
- `privatecloud backup restore <name>` - Restores from backup
- `privatecloud backup delete <name>` - Deletes a backup
- Backups include: namespace manifests, Terraform state, kubeconfig, privatecloud.yaml

**Security Hardening**
- Automatic `.gitignore` generation on `privatecloud init`
- Secret masking in logs and output
- Environment variable support for secrets (`${VAR}` syntax)
- File permission warnings for config files

**Enhanced Destroy Command**
- `--yes` flag for non-interactive use
- `--dry-run` to preview destruction
- `--backup/--no-backup` to control pre-destruction backup
- Auto-backup before destruction (configurable)

## Features

- **Provider abstraction** — bare-metal SSH or Proxmox VE via Terraform
- **Terraform runner** — generates, applies, and destroys infrastructure automatically
- **Config auto-write** — Terraform outputs (node IPs) are written back to `privatecloud.yaml`
- **Helm-based service installation** — all services deployed natively via Helm charts
- **Automated teardown** — `privatecloud destroy` removes cloud-provisioned clusters
- **Backup & Restore** — full cluster state backup and recovery
- **Web GUI** — visual dashboard for cluster management
- **Security features** — secret masking, env var support, .gitignore generation
- Installs **K3s Kubernetes** on master + worker nodes
- Deploys production services:
  - Ingress NGINX
  - cert-manager
  - MetalLB
  - Prometheus + Grafana (monitoring)
  - Longhorn (storage)

## Requirements

| Tool | Required |
|------|----------|
| Python 3.9+ | ✅ |
| ssh / scp | ✅ |
| curl | ✅ |
| terraform | ✅ |
| helm | ✅ |
| kubectl | optional |
| flask | for GUI |

Run `privatecloud doctor` to verify your system.

## Install

```bash
pip install privatecloud
```

## Quickstart

```bash
# Initialize
privatecloud init                    # generate privatecloud.yaml and .gitignore
privatecloud doctor                  # check dependencies

# Deploy
privatecloud plan                    # preview the install plan
privatecloud install-cluster         # deploy everything
privatecloud install-cluster --dry-run  # preview without changes

# Manage
privatecloud gui --port 8080         # start web dashboard
privatecloud backup create            # create backup
privatecloud backup list             # list backups
privatecloud backup restore <name>    # restore from backup

# Destroy
privatecloud destroy                 # tear down (with backup prompt)
privatecloud destroy --yes          # skip confirmation
```

## Config File

> **⚠️ DO NOT COMMIT `privatecloud.yaml` OR YOUR TERRAFORM DIRECTORY TO GIT.**
> Your configuration contains secrets (e.g. Proxmox API tokens). A `.gitignore` is auto-generated on `privatecloud init`.

Created automatically by `privatecloud init`:

```yaml
cluster_name: my-private-cloud
provider: bare-metal          # or "proxmox"
k3s_version: v1.29.0+k3s1

nodes:
  - host: 192.168.1.10
    user: root
    role: master
  - host: 192.168.1.11
    user: root
    role: worker

proxmox:
  url: https://192.168.1.100:8006/api2/json
  token_id: root@pam!mytoken
  token_secret: "${PROXMOX_TOKEN}"  # Use env var for secrets
  node: pve
  template: ubuntu-2204-template
  master_count: 1
  worker_count: 2
  storage: local-lvm
  bridge: vmbr0

services:
  metallb: true
  ingress_nginx: true
  cert_manager: true
  monitoring: true
  longhorn: true
```

## Security

### Use Environment Variables for Secrets

```bash
export PROXMOX_TOKEN="your-secret-token"
privatecloud install-cluster
```

In config, reference with `${VAR_NAME}` syntax:
```yaml
proxmox:
  token_secret: "${PROXMOX_TOKEN}"
```

### Protect Your Config File

```bash
chmod 600 privatecloud.yaml
```

### Auto-generated .gitignore

`privatecloud init` automatically creates `.gitignore` with:
- `privatecloud.yaml`
- `terraform/*.tfstate*`
- `backups/`
- `kubeconfig`
- Other sensitive files

## Provider Modules Roadmap

| Provider | Status | Description |
|----------|--------|-------------|
| Bare-metal | ✅ Stable | Direct SSH installation |
| Proxmox | ✅ v0.2.0 | Proxmox VE via Terraform |
| Hetzner | 🔜 v0.4.0 | Hetzner Cloud API |
| LibVirt | 🔜 v0.4.0 | Local KVM/libvirt VMs |
| vSphere | 📋 Backlog | VMware vSphere integration |
| OpenStack | 📋 Backlog | OpenStack integration |

## Roadmap

### v0.4.0
- [ ] Rolling cluster upgrades (`privatecloud upgrade`)
- [ ] Idempotent installation (re-running skips completed tasks)
- [ ] Hetzner Cloud provider
- [ ] LibVirt/KVM provider

### v1.0 (Production Ready)
- [ ] High-availability K3s with external DB
- [ ] Built-in etcd backup
- [ ] Add-on marketplace (logging, service mesh)
- [ ] Multi-cluster management

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT