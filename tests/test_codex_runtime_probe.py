from __future__ import annotations

import json
import queue
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import codex_runtime_probe as probe


def _skill_payload(root: Path) -> dict[str, Any]:
    skills = [
        {
            "name": name,
            "description": f"Runtime description for {name}",
            "enabled": True,
            "path": str(root / ".agents/skills" / name / "SKILL.md"),
            "scope": "repo",
        }
        for name in probe.EXPECTED_SKILLS
    ]
    skills.append(
        {
            "name": "system-skill",
            "description": "Unrelated system skill",
            "enabled": True,
            "path": "/isolated/system-skill/SKILL.md",
            "scope": "system",
        }
    )
    return {"data": [{"cwd": str(root), "errors": [], "skills": skills}]}


def _hook_payload(root: Path) -> dict[str, Any]:
    hooks = [
        {
            "enabled": True,
            "eventName": event,
            "handlerType": "command",
            "source": "project",
            "sourcePath": str(root / ".codex/hooks.json"),
            "trustStatus": "untrusted",
        }
        for event in probe.EXPECTED_HOOK_EVENTS
    ]
    return {"data": [{"cwd": str(root), "errors": [], "hooks": hooks, "warnings": []}]}


def _config_payload(root: Path) -> dict[str, Any]:
    return {
        "config": {
            "approval_policy": "on-request",
            "sandbox_mode": "workspace-write",
            "web_search": "indexed",
            "project_root_markers": [".git"],
            "sandbox_workspace_write": {"network_access": False},
            "features": {"multi_agent": True, "memories": False},
            "agents": {"max_threads": 6, "max_depth": 1},
        },
        "layers": [
            {
                "name": {
                    "type": "project",
                    "dotCodexFolder": str(root / ".codex"),
                },
                "config": {"features": {"multi_agent": True}},
            }
        ],
        "origins": {},
    }


def _thread_payload(root: Path) -> dict[str, Any]:
    return {
        "approvalPolicy": "never",
        "cwd": str(root),
        "instructionSources": [str(root / "AGENTS.md")],
        "sandbox": {"type": "readOnly", "networkAccess": False},
        "thread": {
            "ephemeral": True,
            "status": {"type": "idle"},
            "turns": [],
        },
    }


def test_runtime_payload_validators_accept_exact_inventory(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert probe._validate_skills(_skill_payload(root), root)["count"] == 13
    assert probe._validate_hooks(_hook_payload(root), root)["events"] == [
        "sessionStart",
        "stop",
    ]
    assert probe._validate_runtime_config(_config_payload(root), root)["project_layer_loaded"]
    thread, agents = probe._validate_thread(_thread_payload(root), root)
    assert thread["turn_count"] == 0
    assert agents == {"instruction_source": "AGENTS.md"}


def test_runtime_skills_fail_closed_on_extra_repo_skill(tmp_path: Path) -> None:
    payload = _skill_payload(tmp_path)
    payload["data"][0]["skills"].append(
        {
            "name": "unexpected",
            "description": "Unexpected repository skill",
            "enabled": True,
            "path": str(tmp_path / ".agents/skills/unexpected/SKILL.md"),
            "scope": "repo",
        }
    )

    with pytest.raises(probe.ProbeFailure, match="exact expected set"):
        probe._validate_skills(payload, tmp_path)


def test_runtime_hooks_fail_closed_on_wrong_source(tmp_path: Path) -> None:
    payload = _hook_payload(tmp_path)
    payload["data"][0]["hooks"][0]["source"] = "user"

    with pytest.raises(probe.ProbeFailure, match="SessionStart and Stop"):
        probe._validate_hooks(payload, tmp_path)


def test_static_role_inventory_parses_exact_toml(tmp_path: Path) -> None:
    roles_root = tmp_path / ".codex/agents"
    roles_root.mkdir(parents=True)
    for name in probe.EXPECTED_ROLES:
        path = roles_root / f"{name.replace('_', '-')}.toml"
        path.write_text(
            "\n".join(
                (
                    f'name = "{name}"',
                    'description = "Long role description used by the compatibility fixture."',
                    'sandbox_mode = "read-only"',
                    'developer_instructions = "Allowed actions; prohibited actions; handoff."',
                    "",
                )
            ),
            encoding="utf-8",
        )

    assert probe._load_roles(tmp_path) == probe.EXPECTED_ROLES


def test_execpolicy_uses_evaluator_without_running_test_commands(tmp_path: Path) -> None:
    rules = tmp_path / ".codex/rules/default.rules"
    rules.parent.mkdir(parents=True)
    rules.write_text("# fixture\n", encoding="utf-8")
    received: list[tuple[str, ...]] = []
    expected_by_command = {command: expected for _, command, expected in probe.RULE_CASES}

    def fake_runner(
        args: tuple[str, ...],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        received.append(args)
        separator = args.index("--")
        command = args[separator + 1 :]
        decision = expected_by_command[command]
        return subprocess.CompletedProcess(args, 0, json.dumps({"decision": decision}), "")

    decisions = probe._evaluate_execpolicy(
        "codex",
        tmp_path,
        {},
        1,
        runner=fake_runner,
    )

    assert decisions == {
        "ordinary_push": "prompt",
        "force_push": "forbidden",
        "hard_reset": "forbidden",
        "network_transfer": "prompt",
    }
    assert len(received) == 4
    assert all(args[1:3] == ("execpolicy", "check") for args in received)


class _FakeOutput:
    def __init__(self) -> None:
        self.lines: queue.Queue[str | None] = queue.Queue()

    def push(self, value: dict[str, Any]) -> None:
        self.lines.put(json.dumps(value) + "\n")

    def close(self) -> None:
        self.lines.put(None)

    def __iter__(self) -> _FakeOutput:
        return self

    def __next__(self) -> str:
        value = self.lines.get(timeout=2)
        if value is None:
            raise StopIteration
        return value


class _FakeInput:
    def __init__(self, output: _FakeOutput, process: _FakeProcess) -> None:
        self.output = output
        self.process = process
        self.sent: list[dict[str, Any]] = []

    def write(self, value: str) -> int:
        message = json.loads(value)
        self.sent.append(message)
        if "id" in message:
            self.output.push({"method": "diagnostic/ignored", "params": {}})
            self.output.push({"id": message["id"], "result": {"ok": True}})
        return len(value)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.process.finished = True
        self.output.close()
        self.process.stderr.close()


class _FakeProcess:
    def __init__(self) -> None:
        self.finished = False
        self.stdout = _FakeOutput()
        self.stderr = _FakeOutput()
        self.stdin = _FakeInput(self.stdout, self)

    def wait(self, timeout: float) -> int:
        del timeout
        if not self.finished:
            raise subprocess.TimeoutExpired("fake", 1)
        return 0

    def terminate(self) -> None:
        self.finished = True

    def kill(self) -> None:
        self.finished = True


def test_json_line_client_handles_notification_and_matching_response(tmp_path: Path) -> None:
    process = _FakeProcess()

    with probe.JsonLineRpcClient(process, 1, (tmp_path,)) as client:
        response = client.request("skills/list", {}, check="repo_skills")
        client.notify("initialized", {})

    assert response == {"ok": True}
    assert client.notifications == ["diagnostic/ignored"]
    assert process.stdin.sent == [
        {"id": 0, "method": "skills/list", "params": {}},
        {"method": "initialized", "params": {}},
    ]


def test_sanitizer_removes_paths_and_auth_values(tmp_path: Path) -> None:
    message = f"path={tmp_path}/auth.json token=secret OPENAI_API_KEY=topsecret"

    sanitized = probe._sanitize_message(message, (tmp_path,))

    assert str(tmp_path) not in sanitized
    assert "secret" not in sanitized
    assert "topsecret" not in sanitized
    assert "<path>" in sanitized
    assert "<redacted>" in sanitized


def test_initialize_requires_isolated_codex_home(tmp_path: Path) -> None:
    with pytest.raises(probe.ProbeFailure, match="isolated"):
        probe._validate_initialize(
            {
                "codexHome": str(tmp_path / "wrong"),
                "platformFamily": "unix",
                "platformOs": "linux",
            },
            tmp_path / "expected",
        )
