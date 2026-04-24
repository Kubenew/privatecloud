# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in PrivateCloud, please report it responsibly:

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly or use GitHub's private vulnerability reporting
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (if applicable)

### What to Expect

- Acknowledgment within 48 hours
- Regular updates on progress
- Credit in the security advisory (if desired)

## Security Best Practices

When using PrivateCloud:

### 1. Protect Your Config File

```bash
chmod 600 privatecloud.yaml
```

Never commit `privatecloud.yaml` to version control.

### 2. Use Environment Variables for Secrets

Instead of storing secrets in plaintext:

```yaml
# In privatecloud.yaml
proxmox:
  token_secret: "${PROXMOX_API_TOKEN}"
```

Set the environment variable before running:
```bash
export PROXMOX_API_TOKEN="your-secret-token"
privatecloud install-cluster
```

### 3. Create Limited Proxmox API Tokens

Create a token with minimal permissions:

```bash
pveum role add PrivateCloudRole -privs "VM.Allocate VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network Sys.Audit"
pveum user token add root@pam!privatecloud --privs PrivateCloudRole
```

### 4. Network Security

- Use VPN or restricted network access for cluster nodes
- Enable TLS verification (avoid `--insecure` flags in production)
- Firewall cluster nodes appropriately

### 5. Terraform State

Terraform state files may contain sensitive data. Store them securely:

- Use Terraform Cloud or S3 with encryption
- Never commit `.tfstate` files to git
- Enable state encryption at rest

## Known Limitations

- The tool requires root/SSH access to nodes
- Secrets are transmitted via SSH during K3s installation
- Ensure your SSH connections are secured (key-based auth recommended)