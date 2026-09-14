"""ResearchJournal — append-only research process log.

Connects to agent-kernel's EventJournal via IPC, or falls back to
local JSON-lines file when kernel is unavailable.

Every research action (hypothesis, experiment, observation, conclusion)
is recorded as a structured event with timestamp, type, and payload.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class EventType(str, Enum):
    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    OBSERVATION = "observation"
    CONCLUSION = "conclusion"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    NOTE = "note"


@dataclass
class JournalEvent:
    id: str
    timestamp: float
    type: EventType
    payload: dict
    parent_id: str | None = None  # links to hypothesis for experiments

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ResearchJournal:
    """Append-only research process journal.

    Two backends:
    1. agent-kernel EventJournal (when IPC available)
    2. Local JSONL file (fallback)
    """

    def __init__(self, session_id: str | None = None, log_dir: str | None = None,
                 kernel_socket: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._kernel = None
        self._log_path = None

        # Try kernel connection
        if kernel_socket:
            try:
                from src.orchestrator.kernel_bridge import AgentKernelBridge
                self._kernel = AgentKernelBridge(kernel_socket)
            except Exception:
                pass

        # Fallback: local JSONL log
        if self._kernel is None:
            log_dir = log_dir or os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "journal"
            )
            os.makedirs(log_dir, exist_ok=True)
            self._log_path = os.path.join(log_dir, f"{self.session_id}.jsonl")

    def _emit(self, event: JournalEvent):
        """Write event to backend."""
        if self._kernel:
            try:
                self._kernel.append_event(
                    event_type=event.type.value,
                    payload=event.to_dict(),
                )
                return
            except Exception:
                pass

        # Fallback: append to local file
        if self._log_path:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")

    # ── High-level API ──

    def log_hypothesis(self, question: str, prediction: str,
                       assumptions: list[str] | None = None) -> str:
        """Record a research hypothesis. Returns hypothesis ID."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.HYPOTHESIS,
            payload={
                "question": question,
                "prediction": prediction,
                "assumptions": assumptions or [],
            },
        )
        self._emit(event)
        return event.id

    def log_experiment(self, tool: str, params: dict, hypothesis_id: str | None = None) -> str:
        """Record the start of an experiment. Returns experiment ID."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.EXPERIMENT,
            parent_id=hypothesis_id,
            payload={"tool": tool, "params": params},
        )
        self._emit(event)
        return event.id

    def log_observation(self, experiment_id: str, result: Any,
                        duration_ms: float = 0, success: bool = True) -> str:
        """Record the result of an experiment."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.OBSERVATION,
            parent_id=experiment_id,
            payload={
                "result": _serialize_result(result),
                "duration_ms": duration_ms,
                "success": success,
            },
        )
        self._emit(event)
        return event.id

    def log_conclusion(self, hypothesis_id: str, verdict: str,
                       evidence: list[str] | None = None) -> str:
        """Record conclusion about a hypothesis."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.CONCLUSION,
            parent_id=hypothesis_id,
            payload={
                "verdict": verdict,
                "evidence": evidence or [],
            },
        )
        self._emit(event)
        return event.id

    def log_tool_call(self, tool_name: str, params: dict, result: Any,
                      duration_ms: float = 0) -> str:
        """Record a low-level tool call."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.TOOL_CALL,
            payload={
                "tool": tool_name,
                "params": params,
                "result": _serialize_result(result),
                "duration_ms": duration_ms,
            },
        )
        self._emit(event)
        return event.id

    def log_error(self, context: str, error: str) -> str:
        """Record an error."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.ERROR,
            payload={"context": context, "error": error},
        )
        self._emit(event)
        return event.id

    def log_note(self, text: str) -> str:
        """Record a free-form note."""
        event = JournalEvent(
            id=uuid.uuid4().hex[:8],
            timestamp=time.time(),
            type=EventType.NOTE,
            payload={"text": text},
        )
        self._emit(event)
        return event.id

    # ── Query API ──

    def get_events(self, event_type: EventType | None = None,
                   parent_id: str | None = None) -> list[dict]:
        """Retrieve events from journal."""
        if self._kernel:
            try:
                events = self._kernel.get_events(event_type=event_type.value if event_type else None)
                if parent_id:
                    events = [e for e in events if e.get("parent_id") == parent_id]
                return events
            except Exception:
                pass

        # Fallback: read from local file
        if self._log_path and os.path.exists(self._log_path):
            events = []
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        evt = json.loads(line)
                        if event_type and evt.get("type") != event_type.value:
                            continue
                        if parent_id and evt.get("parent_id") != parent_id:
                            continue
                        events.append(evt)
            return events
        return []

    def get_hypothesis_chain(self, hypothesis_id: str) -> dict:
        """Get full hypothesis chain: hypothesis → experiments → observations → conclusion."""
        hypothesis = None
        for evt in self.get_events(EventType.HYPOTHESIS):
            if evt["id"] == hypothesis_id:
                hypothesis = evt
                break

        experiments = self.get_events(EventType.EXPERIMENT, parent_id=hypothesis_id)
        conclusions = self.get_events(EventType.CONCLUSION, parent_id=hypothesis_id)

        observations = []
        for exp in experiments:
            observations.extend(self.get_events(EventType.OBSERVATION, parent_id=exp["id"]))

        return {
            "hypothesis": hypothesis,
            "experiments": experiments,
            "observations": observations,
            "conclusions": conclusions,
        }

    def summary(self) -> dict:
        """Get journal summary statistics."""
        events = self.get_events()
        by_type = {}
        for evt in events:
            t = evt.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "session_id": self.session_id,
            "total_events": len(events),
            "by_type": by_type,
            "log_path": self._log_path,
        }


def _serialize_result(result: Any) -> Any:
    """Serialize result to JSON-safe format."""
    if isinstance(result, (str, int, float, bool, type(None))):
        return result
    if isinstance(result, (list, tuple)):
        return [_serialize_result(r) for r in result]
    if isinstance(result, dict):
        return {k: _serialize_result(v) for k, v in result.items()}
    # Try to get a string representation
    try:
        return str(result)
    except Exception:
        return "<unserializable>"
