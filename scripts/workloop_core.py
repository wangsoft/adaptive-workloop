"""Shared deterministic helpers for adaptive-workloop scripts."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import selectors
import signal
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TextIO


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
SENSITIVE_ENV_NAME_RE = re.compile(
    r"(?i)(?:api[_-]?key|token|secret|password|passwd|authorization|cookie|credential|private[_-]?key)"
)
SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&](?:access_token|api_key|key|signature|sig|token)=)[^&\s]+"
)
MAX_TRACKED_FILE_BYTES = 1024 * 1024
EPISODE_DOCUMENTS = ("contract.md", "progress.md", "handoff.md")
EMPTY_EPISODE_FIELD_RE = re.compile(r"(?m)^[ \t]*(?:-|1\.)[ \t]*(?:[^:\n]+:[ \t]*)?$")
UNRESOLVED_CHOICE_RE = re.compile(
    r"(?m)^[ \t]*-[ \t]+[^:\n]+:[ \t]+[^\n]*[ \t]\|[ \t][^\n]*$"
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<[^>\n]+>")
SKILL_RUNTIME_SURFACES = (
    "SKILL.md",
    ".claude-plugin",
    "agents",
    "scripts",
    "references",
    "assets",
    "packaging.allowlist",
    "evals/adapters",
    "evals/profiles",
    "evals/adapter-contract.md",
    "evals/trigger-cases.json",
    "evals/behavior-cases.json",
    "evals/grader-contract.md",
    "evals/matrix-protocol.md",
    "evals/proposal-contract.md",
    "evals/provider-adapters.md",
    "evals/regression-cases.json",
    "evals/standalone-cases.json",
    "evals/editable-surfaces.json",
    "evals/promotion-policy.json",
)
RELEASE_MANIFEST_SCHEMA = "workloop-release-manifest/1"


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


def secure_directory(path: Path) -> Path:
    """Create a private evidence directory and enforce owner-only access."""

    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def atomic_write_text(path: Path, content: str, *, mode: int = 0o600) -> None:
    """Atomically replace a text artifact, fsyncing file and parent directory."""

    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    elif not path.parent.is_dir():
        raise NotADirectoryError(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def acquire_exclusive_file_lock(path: Path) -> TextIO:
    """Acquire a non-blocking process lock or fail closed."""

    secure_directory(path.parent)
    handle = path.open("a+", encoding="utf-8")
    os.chmod(path, 0o600)
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise RuntimeError(f"output is already locked: {path.parent}") from exc
    return handle


def release_file_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def redact_evidence_text(
    text: str, *, environment: dict[str, str] | None = None
) -> str:
    """Redact known secret shapes and explicitly passed sensitive values."""

    redacted = text
    if environment:
        values = {
            value
            for name, value in environment.items()
            if SENSITIVE_ENV_NAME_RE.search(name) and len(value) >= 8
        }
        for value in sorted(values, key=len, reverse=True):
            redacted = redacted.replace(value, "[REDACTED]")
    for _, pattern in SECRET_RULES:
        redacted = pattern.sub("[REDACTED]", redacted)
    redacted = ASSIGNMENT_RULE.sub(
        lambda match: f"{match.group(1)}=[REDACTED]", redacted
    )
    return SENSITIVE_QUERY_RE.sub(lambda match: match.group(1) + "[REDACTED]", redacted)


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


def proposal_validation_binding(
    path: Path,
    *,
    validator_path: Path,
    base_skill_digest: str,
    candidate_skill_digest: str,
) -> dict[str, Any]:
    """Verify and reduce a proposal-validation attestation to a manifest binding."""

    path = path.expanduser().resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"proposal validation is unreadable: {path}: {exc}") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "workloop-proposal-validation/1"
        or value.get("status") != "validated"
        or value.get("promotion_authorized") is not False
        or value.get("digest") != canonical_json_digest(value, omit={"digest"})
    ):
        raise ValueError("proposal validation has an invalid schema, state, or digest")
    validator = value.get("validator")
    resolved_validator = validator_path.resolve()
    if not isinstance(validator, dict) or validator.get("digest") != file_digest(
        resolved_validator
    ):
        raise ValueError("proposal validation does not bind the current validator")
    proposal = value.get("proposal")
    registry = value.get("registry")
    if not isinstance(proposal, dict) or not isinstance(registry, dict):
        raise ValueError("proposal validation is missing proposal or registry evidence")
    proposal_path = Path(str(proposal.get("path", ""))).expanduser().resolve()
    registry_path = Path(str(registry.get("path", ""))).expanduser().resolve()
    if (
        not proposal_path.is_file()
        or proposal.get("file_digest") != file_digest(proposal_path)
        or not registry_path.is_file()
        or registry.get("file_digest") != file_digest(registry_path)
    ):
        raise ValueError("proposal or registry evidence changed after validation")
    try:
        proposal_value = json.loads(proposal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"proposal evidence is unreadable: {exc}") from exc
    if (
        not isinstance(proposal_value, dict)
        or proposal_value.get("schema") != "workloop-improvement-proposal/2"
        or proposal_value.get("digest")
        != canonical_json_digest(proposal_value, omit={"digest"})
        or proposal.get("digest") != proposal_value.get("digest")
    ):
        raise ValueError("proposal evidence has an invalid schema or digest")
    if (
        value.get("base_skill_digest") != base_skill_digest
        or value.get("candidate_skill_digest") != candidate_skill_digest
    ):
        raise ValueError("proposal validation does not bind this Skill pair")
    surface_id = value.get("surface_id")
    actual_paths = value.get("actual_changed_paths")
    search = value.get("search")
    budgets = value.get("budgets")
    if (
        not isinstance(surface_id, str)
        or not surface_id
        or not isinstance(actual_paths, list)
        or not actual_paths
        or any(not isinstance(item, str) or not item for item in actual_paths)
        or not isinstance(search, dict)
        or not isinstance(budgets, dict)
    ):
        raise ValueError("proposal validation has incomplete bounded-change evidence")
    return {
        "path": str(path),
        "file_digest": file_digest(path),
        "digest": value["digest"],
        "validator_digest": validator["digest"],
        "proposal_path": str(proposal_path),
        "proposal_digest": proposal["digest"],
        "registry_path": str(registry_path),
        "registry_digest": registry["file_digest"],
        "base_skill_digest": base_skill_digest,
        "candidate_skill_digest": candidate_skill_digest,
        "surface_id": surface_id,
        "actual_changed_paths": actual_paths,
        "search": search,
        "budgets": budgets,
    }


def skill_runtime_digest(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    for relative, content_digest in skill_runtime_file_digests(root).items():
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_digest.encode("ascii"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def skill_runtime_file_digests(root: Path) -> dict[str, str]:
    """Return stable content digests for every runtime Skill surface file."""

    root = root.resolve()
    result: dict[str, str] = {}
    for surface in SKILL_RUNTIME_SURFACES:
        path = root / surface
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file() or any(
                part in {"__pycache__", ".ruff_cache"} for part in candidate.parts
            ):
                continue
            relative = candidate.relative_to(root).as_posix()
            result[relative] = file_digest(candidate)
    return dict(sorted(result.items()))


def release_file_digests(root: Path) -> dict[str, str]:
    """Return every regular release file except the self-describing manifest."""

    root = root.resolve()
    result: dict[str, str] = {}
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        relative = candidate.relative_to(root)
        if relative.as_posix() == "release-manifest.json" or any(
            part in {"__pycache__", ".ruff_cache"} for part in relative.parts
        ):
            continue
        result[relative.as_posix()] = file_digest(candidate)
    return dict(sorted(result.items()))


def validate_release_manifest(root: Path) -> dict[str, Any]:
    """Fail closed when a packaged Skill no longer matches its release manifest."""

    root = root.resolve()
    manifest_path = root / "release-manifest.json"
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"release manifest is unreadable: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != RELEASE_MANIFEST_SCHEMA:
        raise ValueError("release manifest has an invalid schema")
    files = value.get("files")
    if not isinstance(files, dict) or any(
        not isinstance(path, str) or not isinstance(digest, str)
        for path, digest in files.items()
    ):
        raise ValueError("release manifest files are invalid")
    actual = release_file_digests(root)
    if files != actual:
        missing = sorted(set(files) - set(actual))
        extra = sorted(set(actual) - set(files))
        changed = sorted(
            path for path in set(files) & set(actual) if files[path] != actual[path]
        )
        raise ValueError(
            "release manifest does not match package files: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )
    if value.get("payload_digest") != canonical_json_digest(files):
        raise ValueError("release manifest payload digest is invalid")
    if value.get("skill_runtime_digest") != skill_runtime_digest(root):
        raise ValueError("release manifest Skill runtime digest is invalid")
    return value


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
    findings.extend(scan_episode_placeholders(episode))
    return findings


def scan_episode_placeholders(episode: Path) -> list[dict[str, Any]]:
    """Find template residue that makes an episode contract non-executable."""

    findings: list[dict[str, Any]] = []
    for name in EPISODE_DOCUMENTS:
        path = episode / name
        if not path.is_file() or path.is_symlink():
            findings.append(
                {"path": name, "line": None, "rule": "missing-episode-document"}
            )
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(
                {"path": name, "line": None, "rule": "unreadable-episode-document"}
            )
            continue
        without_comments = re.sub(
            r"<!--[\s\S]*?-->",
            lambda match: "\n" * match.group(0).count("\n"),
            text,
        )
        checks = (
            ("empty-template-field", EMPTY_EPISODE_FIELD_RE, text),
            ("unresolved-template-choice", UNRESOLVED_CHOICE_RE, text),
            (
                "angle-placeholder",
                ANGLE_PLACEHOLDER_RE,
                without_comments.replace("<skill-dir>", "skill-directory"),
            ),
        )
        seen: set[tuple[int, str]] = set()
        for rule, pattern, candidate_text in checks:
            for match in pattern.finditer(candidate_text):
                line = candidate_text.count("\n", 0, match.start()) + 1
                key = (line, rule)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({"path": name, "line": line, "rule": rule})
    return findings
