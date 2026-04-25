import os
import yaml
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, ValidationError


class ValidationIssue(BaseModel):
    severity: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


def load_config(path: str = "privatecloud.yaml") -> Optional[Dict]:
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except yaml.YAMLError as e:
        return None


def validate_yaml_syntax(path: str = "privatecloud.yaml") -> Tuple[bool, List[ValidationIssue]]:
    issues = []
    
    try:
        with open(path) as f:
            yaml.safe_load(f)
        return True, issues
    except FileNotFoundError:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Config file not found: {path}",
            suggestion="Run 'privatecloud init' to create a default config"
        ))
        return False, issues
    except yaml.YAMLError as e:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Invalid YAML syntax: {e}",
            suggestion="Check YAML indentation and formatting"
        ))
        return False, issues


def validate_provider(provider: str) -> List[ValidationIssue]:
    issues = []
    supported = ["bare-metal", "proxmox"]
    
    if provider not in supported:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Unsupported provider: {provider}",
            field="provider",
            suggestion=f"Supported providers: {', '.join(supported)}"
        ))
    
    return issues


def validate_nodes(nodes: List[Dict], provider: str) -> List[ValidationIssue]:
    issues = []
    
    if provider == "bare-metal":
        if not nodes:
            issues.append(ValidationIssue(
                severity="error",
                message="No nodes configured",
                field="nodes",
                suggestion="Add at least one node with host, user, and role"
            ))
        else:
            for i, node in enumerate(nodes):
                if not node.get("host"):
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"Node {i} missing 'host'",
                        field=f"nodes[{i}].host"
                    ))
                
                ip = node.get("host", "")
                # Validate IPv4, IPv6, or hostname
                ipv4_re = r'^(\d{1,3}\.){3}\d{1,3}$'
                ipv6_re = r'^[0-9a-fA-F:]+$'
                hostname_re = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
                if ip and not (re.match(ipv4_re, ip) or re.match(ipv6_re, ip) or re.match(hostname_re, ip)):
                    issues.append(ValidationIssue(
                        severity="warning",
                        message=f"Node {i} host IP may be invalid: {ip}",
                        field=f"nodes[{i}].host"
                    ))
    else:
        if nodes:
            issues.append(ValidationIssue(
                severity="info",
                message="Nodes are auto-provisioned for provider: " + provider,
                field="nodes"
            ))
    
    return issues


def validate_proxmox_config(config: Dict, provider: str) -> List[ValidationIssue]:
    issues = []
    
    if provider != "proxmox":
        if config:
            issues.append(ValidationIssue(
                severity="warning",
                message="Proxmox config provided but provider is not 'proxmox'",
                field="proxmox"
            ))
        return issues
    
    required_fields = ["url", "token_id", "token_secret"]
    for field in required_fields:
        if not config.get(field):
            issues.append(ValidationIssue(
                severity="error",
                message=f"Missing required Proxmox field: {field}",
                field=f"proxmox.{field}"
            ))
    
    url = config.get("url", "")
    if url and not re.match(r'^https?://', url):
        issues.append(ValidationIssue(
            severity="error",
            message=f"Invalid Proxmox URL: {url}",
            field="proxmox.url",
            suggestion="URL should start with https://"
        ))
    
    if config.get("token_secret") == "your-secret-here":
        issues.append(ValidationIssue(
            severity="error",
            message="Proxmox token_secret is still default placeholder",
            field="proxmox.token_secret",
            suggestion="Generate a real API token in Proxmox UI"
        ))
    
    return issues


def validate_services(services: Dict) -> List[ValidationIssue]:
    issues = []
    
    if not services:
        issues.append(ValidationIssue(
            severity="info",
            message="No services configured",
            field="services"
        ))
    
    known_services = ["metallb", "ingress_nginx", "cert_manager", "monitoring", "longhorn"]
    for key in services:
        if key not in known_services:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Unknown service: {key}",
                field=f"services.{key}"
            ))
    
    return issues


def validate_k3s_version(version: str) -> List[ValidationIssue]:
    issues = []
    
    if not version:
        issues.append(ValidationIssue(
            severity="warning",
            message="No K3s version specified",
            field="k3s_version",
            suggestion="Specify a version like 'v1.29.0+k3s1'"
        ))
        return issues
    
    if not re.match(r'^v\d+\.\d+', version):
        issues.append(ValidationIssue(
            severity="warning",
            message=f"K3s version format may be invalid: {version}",
            field="k3s_version",
            suggestion="Use format like 'v1.29.0+k3s1'"
        ))
    
    return issues


def check_secrets_in_config(config: Dict) -> List[ValidationIssue]:
    issues = []
    
    secret_fields = ["token_secret", "token_id", "password", "secret", "api_key"]
    found_secrets = []
    
    def check_dict(d: Dict, path: str = ""):
        for key, value in d.items():
            if any(secret in key.lower() for secret in secret_fields):
                if value and value not in ["your-secret-here", "", "null"]:
                    found_secrets.append(f"{path}{key}")
            if isinstance(value, dict):
                check_dict(value, f"{path}{key}.")
    
    check_dict(config)
    
    if found_secrets:
        issues.append(ValidationIssue(
            severity="info",
            message=f"Found {len(found_secrets)} potential secrets in config",
            suggestion="Consider using environment variables (${VAR}) for sensitive values"
        ))
    
    return issues


def check_file_permissions(path: str = "privatecloud.yaml") -> List[ValidationIssue]:
    issues = []
    
    p = Path(path)
    if p.exists():
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Config file is world-readable (mode: {oct(mode)})",
                field="permissions",
                suggestion="Run: chmod 600 privatecloud.yaml"
            ))
    
    return issues


def lint_config(path: str = "privatecloud.yaml", fix: bool = False) -> Tuple[bool, List[ValidationIssue]]:
    all_issues = []
    
    valid, syntax_issues = validate_yaml_syntax(path)
    all_issues.extend(syntax_issues)
    
    if not valid:
        return False, all_issues
    
    config = load_config(path)
    if not config:
        return False, all_issues
    
    all_issues.extend(validate_provider(config.get("provider", "")))
    all_issues.extend(validate_nodes(config.get("nodes", []), config.get("provider", "")))
    all_issues.extend(validate_proxmox_config(config.get("proxmox", {}), config.get("provider", "")))
    all_issues.extend(validate_services(config.get("services", {})))
    all_issues.extend(validate_k3s_version(config.get("k3s_version", "")))
    all_issues.extend(check_secrets_in_config(config))
    all_issues.extend(check_file_permissions(path))
    
    has_errors = any(i.severity == "error" for i in all_issues)
    
    return not has_errors, all_issues


def print_validation_report(path: str = "privatecloud.yaml"):
    valid, issues = lint_config(path)
    
    print(f"\n{'='*50}")
    print(f"Config Validation Report: {path}")
    print(f"{'='*50}")
    
    if not issues:
        print("✅ No issues found")
        return
    
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")
    
    print(f"\nSummary: {error_count} errors, {warning_count} warnings, {info_count} info")
    print()
    
    for issue in issues:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "-")
        print(f"{icon} [{issue.severity.upper()}] {issue.message}")
        if issue.field:
            print(f"   Field: {issue.field}")
        if issue.suggestion:
            print(f"   Fix: {issue.suggestion}")
        print()
    
    if error_count > 0:
        print("❌ Validation failed - fix errors before proceeding")
    else:
        print("✅ Validation passed - warnings are informational")


def validate_terraform_config():
    tf_files = list(Path(".").glob("terraform/*.tf"))
    
    if not tf_files:
        return True, []
    
    issues = []
    
    for tf in tf_files:
        content = tf.read_text()
        if "password" in content.lower() or "secret" in content.lower():
            if "variable" not in content.lower():
                issues.append(ValidationIssue(
                    severity="warning",
                    message=f"Potential secret in {tf.name} - use variables for sensitive data",
                    suggestion="Use 'variable \"password\" {}' instead of hardcoding secrets"
                ))
    
    return len([i for i in issues if i.severity == "error"]) == 0, issues