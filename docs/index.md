# PrivateCloud

One-command Kubernetes private cloud installer.

## Features (v0.2.0)

- **Provider abstraction** — bare-metal SSH or Proxmox VE via Terraform
- **Terraform runner** — generates, applies, and destroys infra automatically
- **Config auto-write** — Terraform outputs written back to `privatecloud.yaml`
- **Helm-based services** — Ingress NGINX, cert-manager, MetalLB, Prometheus + Grafana, Longhorn
- **Automated teardown** — `privatecloud destroy` for Terraform-managed clusters

## Quick Start

```bash
pip install privatecloud
privatecloud init
privatecloud doctor
privatecloud plan
privatecloud install-cluster
```

## Architecture

```
privatecloud init          → generates privatecloud.yaml
privatecloud doctor        → checks ssh, curl, helm, terraform
privatecloud plan          → previews cluster config
privatecloud install-cluster
  ├── (if proxmox) terraform init/apply → auto-writes node IPs
  ├── K3s master install via SSH
  ├── K3s worker join via SSH
  ├── Fetch kubeconfig
  └── Helm install services (ingress, cert-manager, metallb, monitoring, longhorn)
privatecloud destroy       → terraform destroy + config cleanup
```