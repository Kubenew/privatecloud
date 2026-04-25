import re
import os
from pathlib import Path
from typing import Any, Dict, Union
import yaml

SECRET_PATTERNS = [
    (r'(token|password|api_key|secret|private_key|proxmox_token|token_secret)[\s]*[:=][\s]*["\']?([^"\'\s]+)', r'\1="***"'),
    (r'([a-f0-9]{32,})', '[HASH-MASKED]'),
    (r'([A-Za-z0-9+\/]{40,})', '[BASE64-MASKED]'),
    (r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', '[UUID-MASKED]'),
]

SECRET_KEYS = {'token', 'password', 'api_key', 'secret', 'private_key', 'token_secret', 'api_token', 'token_id', 'token_secret'}


def mask_secrets(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def mask_dict_secrets(data: Union[Dict[str, Any], Any]) -> Union[Dict[str, Any], Any]:
    if not isinstance(data, dict):
        return data
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(secret in key_lower for secret in SECRET_KEYS):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_dict_secrets(value)
        elif isinstance(value, list):
            masked[key] = [mask_dict_secrets(v) if isinstance(v, dict) else v for v in value]
        else:
            masked[key] = value
    return masked


def load_config_with_env(config_path: str = "privatecloud.yaml") -> Dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError("Config file not found")

    content = p.read_text(encoding="utf-8")
    content = _substitute_env_vars(content)
    return yaml.safe_load(content)


def _substitute_env_vars(content: str) -> str:
    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        env_var = match.group(1)
        value = os.environ.get(env_var)
        if value is None:
            raise ValueError(f"Environment variable {env_var} not set (required for config)")
        return value

    return pattern.sub(replacer, content)


def write_gitignore(dest_dir: Path = Path(".")) -> bool:
    content = """# PrivateCloud specific
privatecloud.yaml
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform/
terraform/.terraform.lock.hcl
*.secrets
*.env
backup_*/
kubeconfig

# General secrets
**/.env
**/.secrets
**/*.pem
**/*.key
**/*-secret.yaml

# Kubernetes
.kube/config
"""

    gitignore_path = dest_dir / ".gitignore"
    created = False
    if not gitignore_path.exists():
        gitignore_path.write_text(content)
        created = True
    else:
        current = gitignore_path.read_text()
        if "# PrivateCloud specific" not in current:
            gitignore_path.write_text(current.rstrip() + "\n" + content)
            created = True
    return created


def check_file_permissions(path: str = "privatecloud.yaml") -> None:
    p = Path(path)
    if p.exists():
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            import warnings
            warnings.warn(
                f"⚠️  Warning: {path} is world-readable (mode {oct(mode)}). "
                "Run: chmod 600 privatecloud.yaml"
            )