import os
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Optional
from packaging.version import Version


def get_git_tags() -> List[str]:
    result = subprocess.run(
        ["git", "tag", "--sort=-v:refname"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode == 0:
        return [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
    return []


def get_commits_between_tags(from_tag: str, to_tag: str) -> List[Dict]:
    result = subprocess.run(
        ["git", "log", f"{from_tag}..{to_tag}", "--pretty=format:%s|%an|%ad", "--date=short"],
        capture_output=True,
        text=True,
        check=False
    )
    
    commits = []
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    commits.append({
                        'message': parts[0],
                        'author': parts[1],
                        'date': parts[2],
                    })
    return commits


def categorize_commit(message: str) -> str:
    message_lower = message.lower()
    
    if any(x in message_lower for x in ['fix', 'bug', 'patch', 'hotfix']):
        return 'bugfix'
    elif any(x in message_lower for x in ['feat', 'add', 'new', 'implement']):
        return 'feature'
    elif any(x in message_lower for x in ['doc', 'readme', 'changelog']):
        return 'docs'
    elif any(x in message_lower for x in ['test', 'spec']):
        return 'testing'
    elif any(x in message_lower for x in ['refactor', 'clean', 'optimize']):
        return 'refactor'
    elif any(x in message_lower for x in ['security', 'auth', 'encrypt']):
        return 'security'
    elif any(x in message_lower for x in ['backup', 'restore', 'snapshot']):
        return 'backup'
    elif any(x in message_lower for x in ['gui', 'dashboard', 'web']):
        return 'gui'
    elif any(x in message_lower for x in ['upgrade', 'migrate', 'update version']):
        return 'upgrade'
    else:
        return 'other'


def generate_changelog(versions: Optional[int] = 3) -> str:
    tags = get_git_tags()
    
    if not tags:
        return generate_initial_changelog()
    
    changelog_lines = [
        "# Changelog",
        "",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]
    
    for i, tag in enumerate(tags[:versions]):
        prev_tag = tags[i + 1] if i + 1 < len(tags) else None
        
        version = tag.lstrip('v')
        date_result = subprocess.run(
            ["git", "log", tag, "-1", "--format=%ad", "--date=short"],
            capture_output=True,
            text=True,
            check=False
        )
        date = date_result.stdout.strip() if date_result.returncode == 0 else "unknown"
        
        changelog_lines.append(f"## [{version}] - {date}")
        changelog_lines.append("")
        
        if prev_tag:
            commits = get_commits_between_tags(prev_tag, tag)
            
            by_category = {
                'feature': [],
                'bugfix': [],
                'security': [],
                'backup': [],
                'gui': [],
                'docs': [],
                'other': [],
            }
            
            for commit in commits:
                cat = categorize_commit(commit['message'])
                if cat in by_category:
                    by_category[cat].append(commit['message'])
            
            for cat, messages in by_category.items():
                if messages:
                    cat_title = {
                        'feature': 'Features',
                        'bugfix': 'Bug Fixes',
                        'security': 'Security',
                        'backup': 'Backup & Restore',
                        'gui': 'GUI & Web',
                        'docs': 'Documentation',
                    }.get(cat, cat.title())
                    
                    changelog_lines.append(f"### {cat_title}")
                    for msg in messages[:10]:
                        changelog_lines.append(f"- {msg}")
                    changelog_lines.append("")
        
        changelog_lines.append("")
    
    return '\n'.join(changelog_lines)


def generate_initial_changelog() -> str:
    return f"""# Changelog

Generated: {datetime.datetime.now().strftime('%Y-%m-%d')}

## [0.7.0] - {datetime.datetime.now().strftime('%Y-%m-%d')}

### Features
- Cluster upgrade command with dry-run support
- Multi-cluster management (list, add, switch, remove)
- Add-on marketplace with Helm integration
- Configuration linting and validation

### Backup & Restore
- Cloud storage integration (S3, GCS, Azure)
- Encrypted backups with age
- Scheduled backups (cron/systemd)
- etcd snapshots
- Longhorn snapshot management

### Security
- GUI authentication
- Secret masking in logs
- Auto-generated .gitignore
- Environment variable secrets

### GUI
- Cluster metrics dashboard
- Node/Pod status monitoring
- Longhorn health display
- One-click backup/restore/destroy

### Other
- Comprehensive diagnostics (doctor --diagnostics)
- Terraform state auto-backup before destroy
- Enhanced error handling
"""


def generate_release_notes(version: str, prev_version: Optional[str] = None) -> str:
    if prev_version:
        commits = get_commits_between_tags(f"v{prev_version}", f"v{version}")
    else:
        commits = []
    
    features = []
    bugfixes = []
    breaking = []
    other = []
    
    for commit in commits:
        msg = commit['message']
        cat = categorize_commit(msg)
        
        if cat == 'feature':
            features.append(msg)
        elif cat == 'bugfix':
            bugfixes.append(msg)
        elif 'breaking' in msg.lower():
            breaking.append(msg)
        else:
            other.append(msg)
    
    lines = [
        f"# Release {version}",
        "",
        f"**Release Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]
    
    if breaking:
        lines.extend([
            "## ⚠️ Breaking Changes",
            "",
            *[f"- {b}" for b in breaking],
            "",
        ])
    
    if features:
        lines.extend([
            "## ✨ New Features",
            "",
            *[f"- {f}" for f in features],
            "",
        ])
    
    if bugfixes:
        lines.extend([
            "## 🐛 Bug Fixes",
            "",
            *[f"- {b}" for b in bugfixes],
            "",
        ])
    
    if other:
        lines.extend([
            "## 📝 Other Changes",
            "",
            *[f"- {o}" for o in other],
            "",
        ])
    
    lines.extend([
        "## Installation",
        "",
        "```bash",
        f"pip install privatecloud=={version.lstrip('v')}",
        "```",
        "",
        "## Upgrade",
        "",
        "```bash",
        "pip install --upgrade privatecloud",
        "```",
        "",
    ])
    
    return '\n'.join(lines)


def write_changelog():
    changelog_path = Path("CHANGELOG.md")
    
    current = changelog_path.read_text() if changelog_path.exists() else ""
    generated = generate_changelog(versions=5)
    
    if current and "# Changelog" in current:
        existing = current.split("# Changelog")[1].split("## [")[0]
        new_content = generated + "\n---\n" + existing
    else:
        new_content = generated
    
    changelog_path.write_text(new_content)
    print(f"Updated CHANGELOG.md")


def get_version_from_pyproject() -> str:
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        for line in pyproject.read_text().split('\n'):
            if line.strip().startswith('version'):
                return line.split('=')[1].strip().strip('"')
    return "0.7.0"


def create_release_md(output_dir: Path = Path(".")):
    version = get_version_from_pyproject()
    tags = get_git_tags()
    prev_version = tags[1] if len(tags) > 1 else None
    
    release_notes = generate_release_notes(f"v{version}", prev_version)
    
    release_file = output_dir / f"RELEASE-{version}.md"
    release_file.write_text(release_notes)
    print(f"Created {release_file}")
    
    return str(release_file)