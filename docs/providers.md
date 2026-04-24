# Providers

PrivateCloud supports pluggable infrastructure providers. The provider is set in your `privatecloud.yaml`:

```yaml
provider: bare-metal   # or "proxmox"
```

## Bare-metal (default)

The default provider. You manually specify node IPs in the `nodes:` list and PrivateCloud connects via SSH to install K3s.

No Terraform is involved — nodes must already be reachable via SSH.

## Proxmox

The Proxmox provider uses Terraform to automatically provision VMs on a Proxmox VE hypervisor.

### Prerequisites

- A Proxmox VE server with API access
- An API token (see [Proxmox docs](https://pve.proxmox.com/wiki/User_Management#pveum_tokens))
- A cloud-init template prepared on the Proxmox node
- `terraform` installed locally

### Configuration

```yaml
provider: proxmox

proxmox:
  url: https://proxmox.example.com:8006/api2/json
  token_id: root@pam!mytoken
  token_secret: your-api-token-secret
  node: pve
  template: ubuntu-2204-template
  master_count: 1
  worker_count: 2
  storage: local-lvm
  bridge: vmbr0
  master_cores: 2
  master_memory: 2048
  master_disk: "20G"
  worker_cores: 4
  worker_memory: 8192
  worker_disk: "80G"
```

### Workflow

1. `privatecloud install-cluster` generates a Terraform `main.tf`
2. Runs `terraform init` and `terraform apply`
3. Captures the VM IPs from Terraform outputs
4. Writes the IPs back to `privatecloud.yaml` automatically
5. Proceeds with K3s installation and Helm service deployment

### Teardown

```bash
privatecloud destroy
```

This runs `terraform destroy` and clears the nodes from your config.

## Adding a new provider

To add support for a new provider (e.g., Hetzner, LibVirt):

1. Create a Jinja2 template in `privatecloud/templates/<provider>.tf.j2`
2. Add a config model in `config.py`
3. Add the provider name to `SUPPORTED_PROVIDERS`
4. Handle the new provider in `terraform.py:generate_tf()`
