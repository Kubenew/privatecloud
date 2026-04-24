# Installation

## Requirements

| Tool | Required | Purpose |
|------|----------|---------|
| Python 3.9+ | ✅ | Runtime |
| ssh / scp | ✅ | Node access |
| curl | ✅ | K3s download |
| terraform | ✅ | Infrastructure provisioning |
| helm | ✅ | Service deployment |
| kubectl | optional | Cluster management |

## Install from PyPI

```bash
pip install privatecloud
```

## Install from source

```bash
git clone https://github.com/Kubenew/privatecloud.git
cd privatecloud
pip install -e ".[dev]"
```

## Verify installation

```bash
privatecloud doctor
```

This checks that all required tools (`ssh`, `scp`, `curl`, `helm`, `terraform`) are available in your PATH.