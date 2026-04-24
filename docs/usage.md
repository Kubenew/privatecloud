# Usage

## Initialize configuration

```bash
privatecloud init
```

This creates a `privatecloud.yaml` file in the current directory with sensible defaults.

## Check dependencies

```bash
privatecloud doctor
```

## Preview the plan

```bash
privatecloud plan
```

Displays the cluster name, provider, K3s version, node list, and enabled services.

## Install the cluster

```bash
privatecloud install-cluster
```

This will:

1. **Provision nodes** (if using a Terraform-managed provider like `proxmox`)
2. **Install K3s** on the master node via SSH
3. **Join workers** to the cluster
4. **Fetch kubeconfig** from the master
5. **Deploy services** via Helm (Ingress NGINX, cert-manager, MetalLB, monitoring, Longhorn)

### Dry run

```bash
privatecloud install-cluster --dry-run
```

Preview which services would be installed without making any changes.

## Destroy the cluster

```bash
privatecloud destroy
```

For Terraform-managed providers (`proxmox`), this runs `terraform destroy` and clears the node list from your configuration file.

> **Note:** Destroy is only supported for cloud providers managed by Terraform. Bare-metal nodes must be cleaned up manually.

## Using the Proxmox provider

1. Set `provider: proxmox` in your `privatecloud.yaml`
2. Configure the `proxmox:` block with your API credentials and VM settings
3. Run `privatecloud install-cluster`

Terraform will provision the VMs and automatically write the node IPs back into your config file.

```yaml
provider: proxmox
proxmox:
  url: https://proxmox.example.com:8006/api2/json
  token_id: root@pam!mytoken
  token_secret: your-secret
  node: pve
  template: ubuntu-2204-template
  master_count: 1
  worker_count: 2
  storage: local-lvm
  bridge: vmbr0
```

## After installation

```bash
export KUBECONFIG=./kubeconfig.yaml
kubectl get nodes
kubectl get pods -A
```