"""Append-only search-ledger contracts for governed Harness improvement."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable

from workloop_core import canonical_json_digest, file_digest


EVENT_SCHEMA = "workloop-search-event/1"
SUMMARY_SCHEMA = "workloop-search-ledger-summary/1"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
EVIDENCE_CLASSES = {"public", "held-in", "held-out", "audit-held-out"}
CONDITIONS = ("bare", "previous", "candidate")


class SearchLedgerError(ValueError):
    pass


def normalized_ledger_path(path: Path, *, must_exist: bool) -> Path:
    path = path.expanduser().absolute()
    if path.is_symlink():
        raise SearchLedgerError(f"search ledger must not be a symlink: {path}")
    if must_exist:
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError as exc:
            raise SearchLedgerError(f"search ledger not found: {path}") from exc
        if not stat.S_ISREG(mode):
            raise SearchLedgerError(f"search ledger must be a regular file: {path}")
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SearchLedgerError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SearchLedgerError(f"{path}: root must be an object")
    return value


def valid_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise SearchLedgerError(f"{label} must be a sha256 digest")
    return value


def nonnegative_number(value: Any) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    ):
        return float(value)
    return None


def comparison_record(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    report = load_json(path)
    if report.get("schema") != "workloop-eval-comparison/1" or report.get(
        "digest"
    ) != canonical_json_digest(report, omit={"digest"}):
        raise SearchLedgerError(f"{path}: invalid comparison schema or digest")
    envelope = report.get("compatible_envelope")
    conditions = report.get("conditions")
    if not isinstance(envelope, dict) or not isinstance(conditions, dict):
        raise SearchLedgerError(f"{path}: comparison envelope is incomplete")
    dataset = envelope.get("dataset")
    proposal = envelope.get("proposal_validation")
    if not isinstance(dataset, dict) or not isinstance(proposal, dict):
        raise SearchLedgerError(f"{path}: comparison lacks dataset or proposal binding")
    evidence_class = dataset.get("evidence_class")
    if evidence_class not in EVIDENCE_CLASSES:
        raise SearchLedgerError(f"{path}: invalid evidence class")
    search = proposal.get("search")
    if not isinstance(search, dict):
        raise SearchLedgerError(f"{path}: proposal search binding is missing")
    round_index = search.get("round")
    candidate_index = search.get("candidate_index")
    if (
        not isinstance(round_index, int)
        or isinstance(round_index, bool)
        or round_index < 1
        or not isinstance(candidate_index, int)
        or isinstance(candidate_index, bool)
        or candidate_index < 1
    ):
        raise SearchLedgerError(f"{path}: proposal search indexes are invalid")
    base_digest = valid_digest(
        proposal.get("base_skill_digest"), "proposal base_skill_digest"
    )
    candidate_digest = valid_digest(
        proposal.get("candidate_skill_digest"), "proposal candidate_skill_digest"
    )
    if (
        conditions.get("previous", {}).get("skill_digest") != base_digest
        or conditions.get("candidate", {}).get("skill_digest") != candidate_digest
    ):
        raise SearchLedgerError(f"{path}: comparison Skill binding mismatch")

    totals: list[int] = []
    costs: list[float | None] = []
    durations: list[float | None] = []
    for condition in CONDITIONS:
        metrics = conditions.get(condition)
        if not isinstance(metrics, dict):
            raise SearchLedgerError(f"{path}: missing {condition} metrics")
        total = metrics.get("total")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise SearchLedgerError(f"{path}: invalid {condition} trial total")
        totals.append(total)
        costs.append(
            nonnegative_number(
                metrics.get("usage", {}).get("combined", {}).get("cost_usd")
            )
        )
        durations.append(
            nonnegative_number(metrics.get("duration_seconds", {}).get("combined"))
        )
    resources = {
        "trials": sum(totals),
        "cost_usd": (
            round(sum(value for value in costs if value is not None), 6)
            if all(value is not None for value in costs)
            else None
        ),
        "duration_seconds": (
            round(sum(value for value in durations if value is not None), 3)
            if all(value is not None for value in durations)
            else None
        ),
    }
    return {
        "path": str(path),
        "file_digest": file_digest(path),
        "digest": report["digest"],
        "evidence_class": evidence_class,
        "base_skill_digest": base_digest,
        "candidate_skill_digest": candidate_digest,
        "proposal_validation_digest": valid_digest(
            proposal.get("digest"), "proposal validation digest"
        ),
        "proposal_digest": valid_digest(
            proposal.get("proposal_digest"), "proposal digest"
        ),
        "round": round_index,
        "candidate_index": candidate_index,
        "resources": resources,
    }


def _parse_events(path: Path) -> list[dict[str, Any]]:
    path = normalized_ledger_path(path, must_exist=True)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SearchLedgerError(f"cannot read search ledger: {exc}") from exc
    if not lines:
        raise SearchLedgerError("search ledger is empty")
    events: list[dict[str, Any]] = []
    previous_digest = None
    for line_number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SearchLedgerError(f"search ledger line {line_number}: {exc}") from exc
        if (
            not isinstance(event, dict)
            or set(event)
            != {
                "schema",
                "seq",
                "at",
                "previous_digest",
                "kind",
                "payload",
                "digest",
            }
            or event.get("schema") != EVENT_SCHEMA
            or event.get("seq") != line_number
            or event.get("previous_digest") != previous_digest
            or not isinstance(event.get("payload"), dict)
            or event.get("digest") != canonical_json_digest(event, omit={"digest"})
        ):
            raise SearchLedgerError(f"search ledger line {line_number} is invalid")
        events.append(event)
        previous_digest = event["digest"]
    return events


def validate_search_ledger(
    path: Path,
    *,
    require_closed: bool = False,
) -> dict[str, Any]:
    path = normalized_ledger_path(path, must_exist=True)
    events = _parse_events(path)
    first = events[0]
    if first["kind"] != "search.started" or set(first["payload"]) != {
        "search_id",
        "base_skill_digest",
    }:
        raise SearchLedgerError("search ledger must begin with search.started")
    search_id = first["payload"].get("search_id")
    if not isinstance(search_id, str) or not ID_RE.fullmatch(search_id):
        raise SearchLedgerError("search_id is invalid")
    base_digest = valid_digest(
        first["payload"].get("base_skill_digest"), "base_skill_digest"
    )

    candidates: dict[str, dict[str, Any]] = {}
    indexes: dict[int, str] = {}
    comparisons: list[dict[str, Any]] = []
    comparison_digests: set[str] = set()
    selected: dict[str, Any] | None = None
    for event in events[1:]:
        kind = event["kind"]
        payload = event["payload"]
        if selected is not None:
            raise SearchLedgerError("no events are allowed after candidate selection")
        if kind == "comparison.recorded":
            if set(payload) != {"comparison"} or not isinstance(
                payload.get("comparison"), dict
            ):
                raise SearchLedgerError("comparison.recorded payload is invalid")
            recorded = payload["comparison"]
            actual = comparison_record(Path(str(recorded.get("path", ""))))
            if recorded != actual:
                raise SearchLedgerError("recorded comparison evidence has drifted")
            if recorded.get("digest") in comparison_digests:
                raise SearchLedgerError("duplicate comparison in search ledger")
            if recorded.get("base_skill_digest") != base_digest:
                raise SearchLedgerError(
                    "comparison base Skill differs from search base"
                )
            candidate_digest = recorded["candidate_skill_digest"]
            candidate_index = recorded["candidate_index"]
            known = candidates.setdefault(
                candidate_digest,
                {
                    "candidate_skill_digest": candidate_digest,
                    "candidate_index": candidate_index,
                    "round": recorded["round"],
                    "proposal_validation_digest": recorded[
                        "proposal_validation_digest"
                    ],
                    "proposal_digest": recorded["proposal_digest"],
                    "evidence_classes": [],
                    "status": "open",
                    "reason": None,
                },
            )
            stable = {
                "candidate_index": candidate_index,
                "round": recorded["round"],
                "proposal_validation_digest": recorded["proposal_validation_digest"],
                "proposal_digest": recorded["proposal_digest"],
            }
            if any(known[key] != value for key, value in stable.items()):
                raise SearchLedgerError(
                    "candidate comparison bindings are inconsistent"
                )
            if known["status"] != "open":
                raise SearchLedgerError("comparison recorded after candidate closure")
            owner = indexes.setdefault(candidate_index, candidate_digest)
            if owner != candidate_digest:
                raise SearchLedgerError("candidate_index is reused")
            if recorded["evidence_class"] in known["evidence_classes"]:
                raise SearchLedgerError("duplicate evidence class for one candidate")
            known["evidence_classes"].append(recorded["evidence_class"])
            comparison_digests.add(recorded["digest"])
            comparisons.append(recorded)
        elif kind == "candidate.closed":
            if set(payload) != {"candidate_skill_digest", "status", "reason"}:
                raise SearchLedgerError("candidate.closed payload is invalid")
            candidate_digest = valid_digest(
                payload.get("candidate_skill_digest"), "candidate Skill digest"
            )
            candidate = candidates.get(candidate_digest)
            if candidate is None or candidate["status"] != "open":
                raise SearchLedgerError("candidate closure has no open candidate")
            status = payload.get("status")
            reason = payload.get("reason")
            if status not in {"rejected", "selected"}:
                raise SearchLedgerError("candidate closure status is invalid")
            if not isinstance(reason, str) or not reason.strip():
                raise SearchLedgerError("candidate closure reason is required")
            candidate["status"] = status
            candidate["reason"] = reason.strip()
            if status == "selected":
                selected = candidate
        else:
            raise SearchLedgerError(f"unsupported search event kind: {kind}")

    if require_closed and not candidates:
        raise SearchLedgerError("search ledger contains no candidate evidence")
    if require_closed and any(item["status"] == "open" for item in candidates.values()):
        raise SearchLedgerError("all search candidates must be closed")
    if require_closed and selected is None:
        raise SearchLedgerError("search ledger has no selected candidate")

    resource_costs = [item["resources"]["cost_usd"] for item in comparisons]
    resource_durations = [item["resources"]["duration_seconds"] for item in comparisons]
    summary = {
        "schema": SUMMARY_SCHEMA,
        "path": str(path),
        "file_digest": file_digest(path),
        "head_digest": events[-1]["digest"],
        "search_id": search_id,
        "base_skill_digest": base_digest,
        "candidate_count": len(candidates),
        "max_round": max((item["round"] for item in candidates.values()), default=0),
        "evidence_class_counts": dict(
            sorted(Counter(item["evidence_class"] for item in comparisons).items())
        ),
        "resources": {
            "trials": sum(item["resources"]["trials"] for item in comparisons),
            "cost_usd": (
                round(sum(value for value in resource_costs if value is not None), 6)
                if all(value is not None for value in resource_costs)
                else None
            ),
            "duration_seconds": (
                round(
                    sum(value for value in resource_durations if value is not None), 3
                )
                if all(value is not None for value in resource_durations)
                else None
            ),
        },
        "candidates": sorted(
            candidates.values(), key=lambda item: item["candidate_index"]
        ),
        "comparisons": comparisons,
        "selected_candidate": selected,
    }
    return summary


def initialize_search_ledger(
    path: Path, *, search_id: str, base_skill_digest: str
) -> None:
    if not ID_RE.fullmatch(search_id):
        raise SearchLedgerError("search_id is invalid")
    valid_digest(base_skill_digest, "base_skill_digest")
    path = normalized_ledger_path(path, must_exist=False)
    if path.exists():
        raise SearchLedgerError(f"search ledger already exists: {path}")
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    event = {
        "schema": EVENT_SCHEMA,
        "seq": 1,
        "at": utc_now(),
        "previous_digest": None,
        "kind": "search.started",
        "payload": {
            "search_id": search_id,
            "base_skill_digest": base_skill_digest,
        },
    }
    event["digest"] = canonical_json_digest(event)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise SearchLedgerError(f"search ledger already exists: {path}") from exc
    try:
        os.write(descriptor, (json.dumps(event, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def append_search_event(
    path: Path,
    *,
    kind: str,
    build_payload: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    path = normalized_ledger_path(path, must_exist=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SearchLedgerError(
                    f"search ledger is already locked: {path}"
                ) from exc
            summary = validate_search_ledger(path)
            payload = build_payload(summary)
            events = _parse_events(path)
            event = {
                "schema": EVENT_SCHEMA,
                "seq": len(events) + 1,
                "at": utc_now(),
                "previous_digest": events[-1]["digest"],
                "kind": kind,
                "payload": payload,
            }
            event["digest"] = canonical_json_digest(event)
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return event
    except OSError as exc:
        raise SearchLedgerError(f"cannot append search ledger: {exc}") from exc
