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
