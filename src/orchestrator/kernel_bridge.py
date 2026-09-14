"""Agent-kernel IPC bridge — Python client for the C++ agent-kernel daemon.

Communicates over Unix domain socket using newline-delimited JSON.

Protocol:
  Request:  {"id": "...", "method": "...", "params": {...}}
  Response: {"ok": true, "data": {...}} or {"ok": false, "error": "..."}
"""

from __future__ import annotations

import json
import os
import socket
import uuid
from typing import Any

DEFAULT_SOCKET = "/tmp/agent-kernel.sock"


class AgentKernelBridge:
    """Python client for the C++ agent-kernel IPC daemon."""

    def __init__(self, socket_path: str = DEFAULT_SOCKET):
        self.socket_path = socket_path
        self._sock: socket.socket | None = None

    def connect(self):
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(self.socket_path)

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def _call(self, method: str, params: dict | None = None) -> dict:
        if self._sock is None:
            self.connect()
        request = {"id": uuid.uuid4().hex[:8], "method": method, "params": params or {}}
        self._sock.sendall((json.dumps(request) + "\n").encode())
        buf = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
        resp = json.loads(buf.decode().strip())
        if not resp.get("ok"):
            raise RuntimeError(f"Kernel error: {resp.get('error', 'unknown')}")
        return resp.get("data", {})

    # ── Agent management ──

    def create_agent(self, name: str, role: str = "researcher",
                     department: str = "research") -> dict:
        aid = uuid.uuid4().hex[:12]
        result = self._call("createAgent", {"id": aid, "name": name, "role": role, "department": department})
        result["entityId"] = result.get("entityId", 0)
        return result

    def get_agent(self, entity_id: int) -> dict:
        return self._call("getAgent", {"entityId": int(entity_id)})

    def list_agents(self) -> list[dict]:
        return self._call("listAgents")

    # ── Skill management ──

    def add_skill(self, entity_id: int, skill_id: str,
                  category: str = "Research") -> dict:
        return self._call("addSkill", {
            "entityId": int(entity_id), "skillId": skill_id, "category": category,
        })

    def add_skill_xp(self, entity_id: int, skill_id: str, xp: int) -> dict:
        return self._call("addSkillXp", {"entityId": int(entity_id), "skillId": skill_id, "xp": xp})

    def get_skills(self, entity_id: int) -> dict:
        return self._call("getSkills", {"entityId": int(entity_id)})

    # ── Event journal ──

    def append_event(self, event_type: str, payload: dict, entity_id: int = 0) -> dict:
        return self._call("appendEvent", {
            "entityId": int(entity_id), "eventType": event_type,
            "payload": json.dumps(payload),
        })

    def get_events(self, event_type: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if event_type:
            params["eventType"] = event_type
        return self._call("getEvents", params)

    # ── Messaging ──

    def send_message(self, from_id: int, to_id: int, content: str) -> dict:
        return self._call("sendMessage", {"fromId": int(from_id), "toId": int(to_id), "content": content})

    def get_messages(self, entity_id: int) -> list[dict]:
        return self._call("getMessages", {"entityId": int(entity_id)})

    # ── Simulation ──

    def agent_tick(self, entity_id: int) -> dict:
        return self._call("agentTick", {"entityId": int(entity_id)})

    def run_simulation(self, entity_ids: list[int], ticks: int = 10) -> dict:
        return self._call("runSimulation", {"agentIds": entity_ids, "ticks": ticks})

    # ── Research helpers ──

    def register_research_agent(self, name: str) -> dict:
        agent = self.create_agent(name)
        eid = agent["entityId"]
        mapping_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json")
        n = 0
        if os.path.exists(mapping_path):
            with open(mapping_path) as f:
                mapping = json.load(f)
            for skill_name, info in mapping.items():
                if skill_name.startswith("_"):
                    continue
                self.add_skill(eid, skill_name, info.get("category", "Research"))
                n += 1
        return {"entityId": eid, "name": name, "skills_registered": n}
