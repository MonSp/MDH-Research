"""Agent-kernel IPC bridge — Python client for the C++ agent-kernel daemon.

Communicates over Unix domain socket using newline-delimited JSON
(matching the C++ UnixSocketServer protocol).

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
        """Connect to the kernel daemon."""
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(self.socket_path)

    def disconnect(self):
        """Disconnect from the kernel daemon."""
        if self._sock:
            self._sock.close()
            self._sock = None

    def _call(self, method: str, params: dict | None = None) -> dict:
        """Send a request and return the response."""
        if self._sock is None:
            self.connect()

        request = {
            "id": uuid.uuid4().hex[:8],
            "method": method,
            "params": params or {},
        }
        data = json.dumps(request) + "\n"
        self._sock.sendall(data.encode("utf-8"))

        # Read response
        buf = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break

        response = json.loads(buf.decode("utf-8").strip())
        if not response.get("ok", False):
            raise RuntimeError(f"Kernel error: {response.get('error', 'unknown')}")
        return response.get("data", {})

    # ── Agent management ──

    def create_agent(self, name: str, role: str = "researcher",
                     department: str = "research") -> dict:
        """Create a new agent in the kernel."""
        return self._call("createAgent", {
            "name": name,
            "role": role,
            "department": department,
        })

    def get_agent(self, agent_id: str) -> dict:
        """Get agent profile."""
        return self._call("getAgent", {"id": agent_id})

    def list_agents(self) -> list[dict]:
        """List all agents."""
        return self._call("listAgents")

    # ── Skill management ──

    def add_skill(self, agent_id: str, skill_name: str,
                  category: str = "Research", description: str = "") -> dict:
        """Add a skill to an agent."""
        return self._call("addSkill", {
            "agentId": agent_id,
            "skillName": skill_name,
            "category": category,
            "description": description,
        })

    def add_skill_xp(self, agent_id: str, skill_name: str, xp: int) -> dict:
        """Add XP to a skill."""
        return self._call("addSkillXp", {
            "agentId": agent_id,
            "skillName": skill_name,
            "xp": xp,
        })

    def get_skills(self, agent_id: str) -> list[dict]:
        """Get agent's skill tree."""
        return self._call("getSkills", {"agentId": agent_id})

    # ── Event journal ──

    def append_event(self, event_type: str, payload: dict) -> dict:
        """Append an event to the journal."""
        return self._call("appendEvent", {
            "type": event_type,
            "payload": payload,
        })

    def get_events(self, event_type: str | None = None,
                   limit: int = 100) -> list[dict]:
        """Get events from the journal."""
        params: dict[str, Any] = {"limit": limit}
        if event_type:
            params["type"] = event_type
        return self._call("getEvents", params)

    # ── Messaging ──

    def send_message(self, from_id: str, to_id: str, content: str) -> dict:
        """Send a message between agents."""
        return self._call("sendMessage", {
            "fromId": from_id,
            "toId": to_id,
            "content": content,
        })

    def get_messages(self, agent_id: str) -> list[dict]:
        """Get messages for an agent."""
        return self._call("getMessages", {"agentId": agent_id})

    # ── Simulation ──

    def agent_tick(self, agent_id: str) -> dict:
        """Run one tick for an agent (perceive → decide → act)."""
        return self._call("agentTick", {"agentId": agent_id})

    def run_simulation(self, agent_ids: list[str], ticks: int = 10) -> dict:
        """Run multi-agent simulation for N ticks."""
        return self._call("runSimulation", {
            "agentIds": agent_ids,
            "ticks": ticks,
        })

    # ── Research-specific helpers ──

    def register_research_agent(self, name: str) -> str:
        """Create a research agent and register all research skills."""
        agent = self.create_agent(name, role="researcher", department="research")
        agent_id = agent["id"]

        # Load skill mapping
        import json as json_mod
        mapping_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json"
        )
        if os.path.exists(mapping_path):
            with open(mapping_path) as f:
                mapping = json_mod.load(f)
            for skill_name, skill_info in mapping.items():
                if skill_name.startswith("_"):
                    continue
                self.add_skill(
                    agent_id,
                    skill_name=skill_name,
                    category=skill_info.get("category", "Research"),
                    description=skill_info.get("description", ""),
                )

        return agent_id

    def log_research_event(self, agent_id: str, event_type: str, payload: dict):
        """Log a research event with agent context."""
        self.append_event(event_type, {
            **payload,
            "agent_id": agent_id,
        })
