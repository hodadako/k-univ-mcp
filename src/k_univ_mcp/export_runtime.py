from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeAlias


@dataclass(slots=True)
class ExportProgress:
    provider: str
    current: int
    total: int
    label: str
    campus_code: str | None = None
    college_code: str | None = None
    department_code: str | None = None
    batch_index: int | None = None


@dataclass(slots=True)
class ExportFailureDiagnostic:
    provider: str
    stage: str
    error_type: str
    message: str
    year: str
    semester: str
    campus_code: str | None = None
    college_code: str | None = None
    department_code: str | None = None
    batch_index: int | None = None


ProgressCallback: TypeAlias = Callable[[ExportProgress], None]
FailureCallback: TypeAlias = Callable[[ExportFailureDiagnostic], None]
