"""Shared deterministic helpers for adaptive-workloop scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SNAPSHOT_SCHEMA = "workloop-repo-snapshot/1"
EXCLUDED_TOP_LEVEL = {".git", ".workloop"}
TRACKED_EPISODE_FILES = {
    "manifest.json",
    "state.json",
    "events.jsonl",
    "contract.md",
    "checks.json",
    "progress.md",
    "handoff.md",
}
IGNORED_EPISODE_ENTRIES = {
    ".state.lock",
    "runtime.json",
    "capabilities.json",
    "evidence",
}
SECRET_RULES = (
    ("private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "provider-token",
        re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    ),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
)
ASSIGNMENT_RULE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|client[_-]?secret)\b"
    r"\s*[:=]\s*[\"']?([^\s\"']{8,})"
)
SAFE_ASSIGNMENT_VALUES = {
    "[redacted]",
    "<redacted>",
    "placeholder",
    "example",
    "dummy",
    "none",
    "null",
}
MAX_TRACKED_FILE_BYTES = 1024 * 1024
SKILL_RUNTIME_SURFACES = ("SKILL.md", "agents", "scripts", "references", "assets")


class BoundedCommandError(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class BoundedCommandResult:
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    finally:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def run_bounded_command(
    argv: list[str],
    *,
    input_bytes: bytes,
    environment: dict[str, str],
    timeout_seconds: float,
    max_output_bytes: int,
    cwd: Path | None = None,
) -> BoundedCommandResult:
    """Run one process group with bounded combined stdout/stderr."""

    started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            cwd=cwd,
            start_new_session=True,
        )
    except OSError as exc:
        raise BoundedCommandError("start_error", str(exc)) from exc
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    selector = selectors.DefaultSelector()
    streams = {process.stdout: bytearray(), process.stderr: bytearray()}
    input_view = memoryview(input_bytes)
    input_offset = 0
    os.set_blocking(process.stdin.fileno(), False)
    if input_view:
        selector.register(process.stdin, selectors.EVENT_WRITE)
    else:
        process.stdin.close()
    for stream in streams:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    total = 0
    deadline = started + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_group(process)
                raise BoundedCommandError(
                    "timeout", f"timed out after {timeout_seconds:g} seconds"
                )
            for key, _ in selector.select(min(remaining, 0.1)):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        written = os.write(
                            stream.fileno(),
                            input_view[input_offset : input_offset + 65536],
                        )
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    input_offset += written
                    if input_offset == len(input_view):
                        selector.unregister(stream)
                        stream.close()
                    continue
                try:
                    chunk = os.read(stream.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                total += len(chunk)
                if total > max_output_bytes:
                    _kill_process_group(process)
                    raise BoundedCommandError(
                        "output_limit",
                        f"output limit exceeded ({max_output_bytes} bytes)",
                    )
                streams[stream].extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _kill_process_group(process)
            raise BoundedCommandError(
                "timeout", f"timed out after {timeout_seconds:g} seconds"
            )
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process)
            raise BoundedCommandError(
                "timeout", f"timed out after {timeout_seconds:g} seconds"
            ) from exc
    finally:
        selector.close()
        if not process.stdin.closed:
            process.stdin.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()
    return BoundedCommandResult(
        returncode=returncode,
        stdout=bytes(streams[process.stdout]).decode("utf-8", errors="replace"),
        stderr=bytes(streams[process.stderr]).decode("utf-8", errors="replace"),
        duration_seconds=time.monotonic() - started,
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def adapter_runtime_digest(path: Path) -> str:
    """Bind a single-file adapter and its conventional shared runtime module."""

    path = path.resolve()
    candidates = [path]
    shared = path.parent / "provider_common.py"
    if path.parent.name == "adapters" and shared.is_file() and shared != path:
        candidates.append(shared)
    digest = hashlib.sha256()
    for candidate in candidates:
        digest.update(candidate.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(candidate.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def canonical_json_digest(value: Any, *, omit: set[str] | None = None) -> str:
    if omit and isinstance(value, dict):
        value = {key: item for key, item in value.items() if key not in omit}
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256_bytes(encoded)


def skill_runtime_digest(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    for surface in SKILL_RUNTIME_SURFACES:
        path = root / surface
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file() or any(
                part in {"__pycache__", ".ruff_cache"} for part in candidate.parts
            ):
                continue
            relative = candidate.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(candidate.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _git(
    root: Path, *args: str, text: bool = False
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
    )


def _included(relative: Path) -> bool:
    return bool(relative.parts) and relative.parts[0] not in EXCLUDED_TOP_LEVEL


def _filesystem_paths(root: Path) -> Iterable[Path]:
    paths: list[Path] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        if relative_dir == Path("."):
            directories[:] = [
                name for name in directories if name not in EXCLUDED_TOP_LEVEL
            ]
        for name in list(directories):
            path = current_path / name
            if path.is_symlink():
                paths.append(path.relative_to(root))
                directories.remove(name)
        directories.sort()
        for name in sorted(files):
            paths.append((current_path / name).relative_to(root))
    yield from sorted(paths)


def _repository_paths(root: Path, inside_git: bool) -> list[Path]:
    if not inside_git:
        return list(_filesystem_paths(root))
    commands = (
        ("diff", "--name-only", "-z", "--", ".", ":(exclude).workloop"),
        (
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--",
            ".",
            ":(exclude).workloop",
        ),
        (
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude).workloop",
        ),
    )
    paths: set[Path] = set()
    for command in commands:
        result = _git(root, *command)
        if result.returncode != 0:
            continue
        paths.update(
            Path(os.fsdecode(raw)) for raw in result.stdout.split(b"\0") if raw
        )
    return sorted(path for path in paths if _included(path))


def _index_records(root: Path) -> list[bytes]:
    result = _git(root, "ls-files", "-z", "--stage")
    if result.returncode != 0:
        return []
    records = []
    for record in result.stdout.split(b"\0"):
        if not record or b"\t" not in record:
            continue
        path_bytes = record.split(b"\t", 1)[1]
        if _included(Path(os.fsdecode(path_bytes))):
            records.append(record)
    return records


def _hash_path(digest: "hashlib._Hash", root: Path, relative: Path) -> None:
    path = root / relative
    digest.update(os.fsencode(relative.as_posix()))
    digest.update(b"\0")
    try:
        metadata = path.lstat()
    except OSError as exc:
        digest.update(f"unreadable:{type(exc).__name__}".encode())
        digest.update(b"\0")
        return
    digest.update(f"mode:{stat.S_IMODE(metadata.st_mode):o}".encode())
    digest.update(b"\0")
    if path.is_symlink():
        digest.update(b"symlink\0")
        digest.update(os.fsencode(os.readlink(path)))
    elif path.is_file():
        digest.update(b"file\0")
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            digest.update(f"unreadable:{type(exc).__name__}".encode())
    elif path.is_dir():
        nested = repository_snapshot(path)
        digest.update(b"nested-repository\0")
        digest.update(nested["state_digest"].encode())
    else:
        digest.update(b"missing\0")
    digest.update(b"\0")


def repository_snapshot(root: Path) -> dict[str, Any]:
    """Hash repository contents, not merely the set of dirty path labels."""

    root = root.resolve()
    inside_result = _git(root, "rev-parse", "--is-inside-work-tree", text=True)
    inside_git = (
        inside_result.returncode == 0 and inside_result.stdout.strip() == "true"
    )
    head: str | None = None
    status = ""
    if inside_git:
        head_result = _git(root, "rev-parse", "HEAD", text=True)
        if head_result.returncode == 0:
            head = head_result.stdout.strip() or None
        status_result = _git(
            root,
            "status",
            "--porcelain=v1",
            "--",
            ".",
            ":(exclude).workloop",
            text=True,
        )
        if status_result.returncode == 0:
            status = status_result.stdout.rstrip("\n")

    paths = _repository_paths(root, inside_git)
    digest = hashlib.sha256()
    digest.update(SNAPSHOT_SCHEMA.encode())
    digest.update(b"\0")
    digest.update((head or "<no-head>").encode())
    digest.update(b"\0")
    digest.update(status.encode())
    digest.update(b"\0")
    if inside_git:
        for record in _index_records(root):
            digest.update(record)
            digest.update(b"\0")
    for relative in paths:
        _hash_path(digest, root, relative)
    return {
        "schema": SNAPSHOT_SCHEMA,
        "head": head,
        "dirty_files": len(status.splitlines()) if status else 0,
        "file_count": len(paths),
        "state_digest": "sha256:" + digest.hexdigest(),
    }


def scan_tracked_episode(episode: Path) -> list[dict[str, Any]]:
    """Return redacted structural and secret findings for Git-visible episode files."""

    findings: list[dict[str, Any]] = []
    names = {path.name for path in episode.iterdir()}
    for missing in sorted(TRACKED_EPISODE_FILES - names):
        findings.append({"path": missing, "line": None, "rule": "missing-file"})
    for unexpected in sorted(names - TRACKED_EPISODE_FILES - IGNORED_EPISODE_ENTRIES):
        findings.append(
            {"path": unexpected, "line": None, "rule": "unexpected-tracked-surface"}
        )

    for name in sorted(TRACKED_EPISODE_FILES & names):
        path = episode / name
        if path.is_symlink() or not path.is_file():
            findings.append({"path": name, "line": None, "rule": "not-regular-file"})
            continue
        try:
            size = path.stat().st_size
            if size > MAX_TRACKED_FILE_BYTES:
                findings.append({"path": name, "line": None, "rule": "file-too-large"})
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append({"path": name, "line": None, "rule": "unreadable-text"})
            continue
        for rule, pattern in SECRET_RULES:
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "path": name,
                        "line": text.count("\n", 0, match.start()) + 1,
                        "rule": rule,
                    }
                )
        for match in ASSIGNMENT_RULE.finditer(text):
            value = match.group(2).rstrip(",;)").lower()
            if value not in SAFE_ASSIGNMENT_VALUES:
                findings.append(
                    {
                        "path": name,
                        "line": text.count("\n", 0, match.start()) + 1,
                        "rule": "secret-assignment",
                    }
                )
    return findings
