import re
import secrets
import shutil
from pathlib import Path

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class JobWorkspace:
    """Isolated filesystem area for one job's temporary artifacts."""

    def __init__(self, root: Path, base_dir: Path):
        self.root = root.resolve()
        self.base_dir = base_dir.resolve()
        if self.root.parent != self.base_dir or self.root == self.base_dir:
            raise ValueError("Job workspace must be a direct child of its base directory")

    @classmethod
    def create(cls, base_dir: Path | str = "/tmp/jobs", job_id: str | None = None) -> "JobWorkspace":
        base = Path(base_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        name = job_id or secrets.token_urlsafe(18)
        root = (base / name).resolve()
        if root.parent != base or root.exists():
            raise ValueError("Invalid or colliding job workspace")
        root.mkdir(mode=0o700)
        return cls(root, base)

    def path(self, filename: str) -> Path:
        safe_name = _SAFE_NAME.sub("_", Path(filename).name).strip(".")
        if not safe_name:
            raise ValueError("filename is required")
        candidate = (self.root / safe_name).resolve()
        if candidate.parent != self.root:
            raise ValueError("path escapes job workspace")
        return candidate

    def cleanup(self) -> None:
        if self.root.parent != self.base_dir or self.root == self.base_dir:
            raise ValueError("Refusing to clean workspace outside its base directory")
        shutil.rmtree(self.root, ignore_errors=False)
