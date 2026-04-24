# PrivateCloud ☁️

**PrivateCloud** is a Python CLI installer that provisions a Kubernetes-based private cloud stack.

It focuses on **fast deployment**, **repeatable infrastructure**, and **production-ready defaults**.

## Features (v0.2.0)

- **Provider abstraction** — bare-metal SSH or Proxmox VE via Terraform
- **Terraform runner** — generates, applies, and destroys infrastructure automatically
- **Config auto-write** — Terraform outputs (node IPs) are written back to `privatecloud.yaml`
- **Helm-based service installation** — all services deployed natively via Helm charts
- **Automated teardown** — `privatecloud destroy` removes cloud-provisioned clusters
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

Run `privatecloud doctor` to verify your system.

## Install

```bash
pip install privatecloud
```

## Quickstart

```bash
privatecloud init          # generate privatecloud.yaml
privatecloud doctor        # check dependencies
privatecloud plan          # preview the install plan
privatecloud install-cluster          # deploy everything
privatecloud install-cluster --dry-run  # preview without changes
privatecloud destroy       # tear down (Terraform providers only)
```

## Config File

> [!WARNING]
> **DO NOT COMMIT `privatecloud.yaml` OR YOUR TERRAFORM DIRECTORY TO GIT.** 
> Your configuration contains secrets (e.g. Proxmox API tokens). Add `privatecloud.yaml` and `.terraform*` to your `.gitignore`.

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
  token_secret: your-secret-here
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

> When `provider: proxmox`, nodes are provisioned dynamically via Terraform and their IPs are auto-written back into the config.

## Provider Modules Roadmap

| Provider | Status | Description |
|----------|--------|-------------|
| Bare-metal | ✅ Stable | Direct SSH installation |
| Proxmox | ✅ v0.2.0 | Proxmox VE via Terraform |
| Hetzner | 🔜 v0.3.0 | Hetzner Cloud API |
| LibVirt | 🔜 v0.3.0 | Local KVM/libvirt VMs |
| vSphere | 📋 Backlog | VMware vSphere integration |
| OpenStack | 📋 Backlog | OpenStack integration |

Contributions welcome!

## License
MIT
