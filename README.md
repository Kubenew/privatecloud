# PrivateCloud ☁️

**PrivateCloud** is a Python CLI installer that provisions a Kubernetes-based private cloud stack.

It focuses on **fast deployment**, **repeatable infrastructure**, and **production-ready defaults**.

## Features (v0.1.0)
- Installs **K3s Kubernetes**
- Installs base cloud services (framework skeleton):
  - Ingress NGINX
  - cert-manager
  - MetalLB
  - Prometheus + Grafana (monitoring)
  - Longhorn (storage)
- Generates install plan + executes scripts
- Works via SSH (bare-metal / VM)

## Install

```bash
pip install privatecloud
```

## Quickstart

```bash
privatecloud init
privatecloud doctor
privatecloud plan
privatecloud install-cluster
```

## Config File

Created automatically:

`privatecloud.yaml`

Example:

```yaml
cluster_name: my-private-cloud
nodes:
  - host: 192.168.1.10
    user: root
  - host: 192.168.1.11
    user: root
k3s_version: v1.29.0+k3s1
services:
  metallb: true
  ingress_nginx: true
  cert_manager: true
  monitoring: true
  longhorn: true
```

## Commands

- `privatecloud init` - create config + folders
- `privatecloud doctor` - check system dependencies
- `privatecloud plan` - print install plan
- `privatecloud install-cluster` - deploy private cloud stack
- `privatecloud install-cluster --dry-run` - preview without installing
- `privatecloud destroy` - placeholder (v0.2.0)

## Provider Modules Roadmap

The following cloud providers are planned for future releases:

| Provider | Status | Description |
|----------|--------|-------------|
| Proxmox | 🔜 v0.2.0 | Proxmox VE integration |
| Hetzner | 🔜 v0.2.0 | Hetzner Cloud API |
| LibVirt | 🔜 v0.3.0 | Local KVM/libvirt VMs |
| vSphere | 📋 Backlog | VMware vSphere integration |
| OpenStack | 📋 Backlog | OpenStack integration |

Contributions welcome!

## License
MIT
