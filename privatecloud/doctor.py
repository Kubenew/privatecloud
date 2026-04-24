import shutil
from dataclasses import dataclass
from typing import List

REQUIRED_TOOLS = ["ssh", "scp", "curl"]
OPTIONAL_TOOLS = ["kubectl", "helm"]


@dataclass
class DoctorResult:
    ok: bool
    missing_required: List[str]
    missing_optional: List[str]


def check_tools() -> DoctorResult:
    missing_required = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    missing_optional = [t for t in OPTIONAL_TOOLS if shutil.which(t) is None]

    return DoctorResult(
        ok=(len(missing_required) == 0),
        missing_required=missing_required,
        missing_optional=missing_optional,
    )
