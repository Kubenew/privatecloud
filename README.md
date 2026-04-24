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
- `privatecloud destroy` - placeholder (v0.2.0)

## License
MIT
