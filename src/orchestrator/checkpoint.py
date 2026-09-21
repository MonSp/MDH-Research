"""L23: research checkpoint snapshots.

Persist a ResearchLoop.run() conclusion (and optional campaign summary)
to a JSON checkpoint for audit / later trend / report reuse.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

DEFAULT_CHECKPOINT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "checkpoints"
)


def _serialize(obj: Any) -> Any:
    from .serialize import serialize_result

    return serialize_result(obj)


def save_checkpoint(
    result: dict,
    path: str | None = None,
    label: str | None = None,
    kind: str = "run",
) -> str:
    """Save a research run/campaign result as a checkpoint file.

    Returns the written path.
    """
    if kind == "campaign":
        payload_src = result.get("summary") or {}
        questions = result.get("questions")
        checkpoint = {
            "kind": "campaign",
            "label": label,
            "ts": time.time(),
            "summary": _serialize(payload_src),
            "n_questions": len(questions or []),
        }
    else:
        conclusion = result.get("conclusion") or {}
        checkpoint = {
            "kind": "run",
            "label": label or result.get("question", "")[:80],
            "ts": time.time(),
            "question": result.get("question"),
            "conclusion": _serialize(conclusion),
            "verdict": conclusion.get("verdict"),
            "competed": conclusion.get("competed"),
            "iterate_rounds": conclusion.get("iterate_rounds"),
        }

    if path is None:
        os.makedirs(DEFAULT_CHECKPOINT_DIR, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (label or "run"))[:40]
        path = os.path.join(
            DEFAULT_CHECKPOINT_DIR,
            f"{int(checkpoint['ts'])}_{safe or 'run'}.json",
        )
    else:
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2, default=str)
    return path


def load_checkpoint(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_checkpoints(dir_path: str | None = None) -> list[dict]:
    d = dir_path or DEFAULT_CHECKPOINT_DIR
    out = []
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "path": p,
            "name": name,
            "kind": data.get("kind"),
            "label": data.get("label"),
            "verdict": data.get("verdict") or (data.get("summary") or {}).get("n_verified"),
            "ts": data.get("ts"),
        })
    return out


def checkpoint_to_run_result(ckpt: dict) -> dict:
    """Convert a saved checkpoint into a pseudo ResearchLoop.run() result
    suitable for report.render_single_run / trend aggregation inputs."""
    if ckpt.get("kind") == "campaign":
        return {"summary": ckpt.get("summary") or {}, "questions": []}
    return {
        "question": ckpt.get("question"),
        "conclusion": ckpt.get("conclusion") or {
            "verdict": ckpt.get("verdict"),
        },
    }


def render_checkpoint(ckpt: dict) -> str:
    if ckpt.get("kind") == "campaign":
        s = ckpt.get("summary") or {}
        return (
            f"# Checkpoint (campaign)\n\n"
            f"- label: {ckpt.get('label')}\n"
            f"- questions: {ckpt.get('n_questions')}\n"
            f"- verify_rate: {s.get('verify_rate')}\n"
            f"- known_value_rate: {s.get('known_value_rate')}\n"
        )
    c = ckpt.get("conclusion") or {}
    return (
        f"# Checkpoint (run)\n\n"
        f"- label: {ckpt.get('label')}\n"
        f"- question: {ckpt.get('question')}\n"
        f"- verdict: {ckpt.get('verdict')}\n"
        f"- competed: {ckpt.get('competed')}  iterate: {ckpt.get('iterate_rounds')}\n"
        f"- n_experiments: {c.get('n_experiments')}\n"
    )
