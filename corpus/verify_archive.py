"""Check the frozen archive after extracting it to a relocated workspace path."""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid

try:
    from .prepare import ROOT
except ImportError:
    from prepare import ROOT


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


@contextmanager
def workspace_copy_dir(workspace: Path):
    workspace = workspace.resolve()
    temporary = workspace / ("abbr relocated copy with spaces " + uuid.uuid4().hex)
    temporary.mkdir()
    try:
        yield temporary
    finally:
        resolved = temporary.resolve()
        if not resolved.is_relative_to(workspace) or resolved.parent != workspace:
            raise RuntimeError("Refusing to remove a path outside the archive workspace")
        shutil.rmtree(temporary)


def verify(archive: Path) -> dict:
    archive = archive.resolve()
    workspace = archive.parent.resolve()
    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    expected, name = sidecar.read_text(encoding="ascii").strip().split("  ", 1)
    actual = file_digest(archive)
    if name != archive.name or expected != actual:
        raise RuntimeError("Archive SHA-256 sidecar mismatch")
    with workspace_copy_dir(workspace) as extracted:
        if not extracted.is_relative_to(workspace):
            raise RuntimeError("Relocated extraction escaped workspace")
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            if not members or any(Path(m.name).is_absolute() or ".." in Path(m.name).parts
                                  or m.name.split("/")[0] != "representative_v1"
                                  or not (m.isfile() or m.isdir()) for m in members):
                raise RuntimeError("Archive has unsafe paths or entries outside representative_v1")
            if sys.version_info >= (3, 12):
                tar.extractall(extracted, filter="data")
            else:
                tar.extractall(extracted)
        bundle = extracted / "representative_v1"
        checked = subprocess.run([sys.executable, str(bundle / "runner/validate_bundle.py"),
                                  "--corpus", str(bundle), "--stage", "input"],
                                 capture_output=True, text=True)
        if checked.returncode:
            raise RuntimeError("Relocated validation failed: " + checked.stdout + checked.stderr)
        report = json.loads(checked.stdout)
    return {"archive": str(archive), "bytes": archive.stat().st_size,
            "sha256": actual, "relocated_input_validation": report}


if __name__ == "__main__":
    print(json.dumps(verify(ROOT / "evaluation/representative_v1.input.tar.gz"),
                     sort_keys=True, indent=2))
