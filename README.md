# PrivateCloud ☁️

**PrivateCloud** is a Python CLI installer that provisions a Kubernetes-based private cloud stack.

It focuses on **fast deployment**, **repeatable infrastructure**, and **production-ready defaults**.
PrivateCloud v0.2.0 Release Notes
We are thrilled to announce PrivateCloud v0.2.0, introducing major architectural upgrades that transform the CLI from a simple SSH-based installer into a powerful, declarative infrastructure-as-code tool.

🚀 New Features
Provider Abstraction & Proxmox Support
PrivateCloud now supports a generic provider abstraction. While bare-metal remains the default, we have officially introduced support for the Proxmox provider via Terraform. You can now define your master and worker VM counts, network bridge, and templates directly in your privatecloud.yaml, and the CLI will dynamically provision them for you.

Embedded Terraform Runner & Auto-Configuration
We have embedded a robust Terraform runner into the privatecloud core.

Dynamic Provisioning: The CLI now automatically generates Terraform manifests based on your configuration.
Config Auto-Write: Following successful execution (terraform apply), PrivateCloud captures the IP addresses of the newly provisioned VMs via Terraform outputs and automatically populates the nodes section of your privatecloud.yaml, maintaining a single source of truth.
Native Helm Integration
Service installation is no longer a placeholder! We have integrated a native Helm runner. After K3s is successfully installed, PrivateCloud now automatically fetches the cluster's kubeconfig and uses Helm to deploy your enabled services natively:

Ingress NGINX
Cert-Manager
MetalLB
Kube-Prometheus-Stack (Monitoring)
Longhorn (Storage)
Automated Cluster Teardown
The privatecloud destroy command has been fully implemented for Terraform-managed providers. It will automatically run terraform destroy to tear down the infrastructure and scrub the deployed nodes from your local configuration file.

🛠️ Requirements
With the introduction of these features, Terraform and Helm are now required dependencies. You can verify your system's readiness by running privatecloud doctor.

📦 Upgrading
You can update your installation using pip:

bash
pip install privatecloud==0.2.0

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
