#!/usr/bin/env python3
"""Read-only, non-model compatibility probe for a packaged Minius workspace."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import tomllib
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

EXPECTED_SKILLS = (
    "case-law-analysis",
    "eu-acquis-analysis",
    "legal-drafting",
    "legal-monitoring",
    "legal-qa-audit",
    "matter-intake",
    "quantitative-impact-analysis",
    "redaction-and-disclosure",
    "session-memory-handoff",
    "source-provenance",
    "ukrainian-legal-research",
    "verifiable-legal-document",
)
EXPECTED_ROLES = (
    "case_law_analyst",
    "document_engineer",
    "eu_law_analyst",
    "evidence_auditor",
    "legal_coordinator",
    "legal_drafter",
    "policy_impact_analyst",
    "privacy_reviewer",
    "quantitative_analyst",
    "ua_law_researcher",
)
EXPECTED_HOOK_EVENTS = ("sessionStart", "stop")
RULE_CASES = (
    ("ordinary_push", ("git", "push", "origin", "main"), "prompt"),
    ("force_push", ("git", "push", "--force", "origin", "main"), "forbidden"),
    ("hard_reset", ("git", "reset", "--hard", "HEAD~1"), "forbidden"),
    ("network_transfer", ("curl", "https://example.invalid"), "prompt"),
)
REQUIRED_CHECKS = (
    "codex_version",
    "workspace_git_root",
    "static_project_config",
    "project_roles",
    "app_server_initialize",
    "runtime_project_config",
    "runtime_agents",
    "repo_skills",
    "project_hooks",
    "thread_start_no_turn",
    "execpolicy",
    "workspace_unchanged",
)
MAX_PROTOCOL_LINE_BYTES = 5 * 1024 * 1024
MAX_DIAGNOSTIC_CHARS = 320


class ProbeFailure(RuntimeError):
    """A classified probe failure safe to expose after sanitization."""

    def __init__(self, check: str, code: str, message: str) -> None:
        super().__init__(message)
        self.check = check
        self.code = code


class RpcFailure(ProbeFailure):
    """A JSON-line app-server protocol failure."""


def _object(value: Any, *, check: str, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProbeFailure(check, "invalid_response", f"{label} is not a JSON object.")
    return value


def _sanitize_message(message: str, private_paths: Sequence[Path]) -> str:
    sanitized = message.replace("\r", " ").replace("\n", " ")
    paths = [*private_paths, Path.home()]
    for path in sorted({str(item) for item in paths if str(item)}, key=len, reverse=True):
        sanitized = sanitized.replace(path, "<path>")
    sanitized = re.sub(
        r"(?i)\b((?:[A-Z0-9]+_)*API[_-]?KEY|authorization|bearer|token)\b"
        r"\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"(?<![\w.])/(?:Users|home|private|tmp|var)/[^\s,'\"]+", "<path>", sanitized)
    sanitized = re.sub(r"\b[A-Za-z]:\\[^\s,'\"]+", "<path>", sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized[:MAX_DIAGNOSTIC_CHARS]


def _toml_string(value: str) -> str:
    # JSON basic strings are also valid TOML basic strings for filesystem paths.
    return json.dumps(value, ensure_ascii=False)


def _isolated_environment(codex_home: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(codex_home)
    for name in (
        "AZURE_OPENAI_API_KEY",
        "CODEX_API_KEY",
        "OPENAI_API_KEY",
        "OPENAI_ADMIN_KEY",
    ):
        environment.pop(name, None)
    return environment


class JsonLineRpcClient:
    """Minimal bounded client for Codex app-server's newline-delimited JSON RPC."""

    def __init__(
        self,
        process: Any,
        timeout_seconds: float,
        private_paths: Sequence[Path],
    ) -> None:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise RpcFailure(
                "app_server_initialize",
                "missing_pipe",
                "Codex app-server did not provide all required standard streams.",
            )
        self._process = process
        self._stdin: TextIO = process.stdin
        self._stdout: TextIO = process.stdout
        self._stderr: TextIO = process.stderr
        self._timeout_seconds = timeout_seconds
        self._private_paths = tuple(private_paths)
        self._response_lines: queue.Queue[str | None] = queue.Queue()
        self._stderr_lines: deque[str] = deque(maxlen=20)
        self._next_id = 0
        self.notifications: list[str] = []
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        try:
            for line in self._stdout:
                self._response_lines.put(line)
        finally:
            self._response_lines.put(None)

    def _read_stderr(self) -> None:
        for line in self._stderr:
            self._stderr_lines.append(line)

    def _send(self, payload: Mapping[str, Any], check: str) -> None:
        try:
            self._stdin.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            self._stdin.flush()
        except (BrokenPipeError, OSError) as error:
            detail = self._server_detail()
            raise RpcFailure(
                check,
                "server_disconnected",
                f"Codex app-server disconnected while receiving a request. {detail}",
            ) from error

    def _server_detail(self) -> str:
        if not self._stderr_lines:
            return "No app-server diagnostic was available."
        return "App-server emitted a diagnostic; inspect it locally before retrying."

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._send({"method": method, "params": params}, "app_server_initialize")

    def request(
        self,
        method: str,
        params: Mapping[str, Any],
        *,
        check: str,
    ) -> Mapping[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"id": request_id, "method": method, "params": params}, check)
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RpcFailure(
                    check,
                    "timeout",
                    f"Codex app-server did not answer {method!r} within the configured timeout.",
                )
            try:
                line = self._response_lines.get(timeout=remaining)
            except queue.Empty as error:
                raise RpcFailure(
                    check,
                    "timeout",
                    f"Codex app-server did not answer {method!r} within the configured timeout.",
                ) from error
            if line is None:
                raise RpcFailure(
                    check,
                    "server_exited",
                    f"Codex app-server exited before answering {method!r}. {self._server_detail()}",
                )
            if len(line.encode("utf-8", errors="replace")) > MAX_PROTOCOL_LINE_BYTES:
                raise RpcFailure(check, "oversized_response", "App-server response exceeded 5 MiB.")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                raise RpcFailure(
                    check,
                    "invalid_json",
                    "Codex app-server returned a non-JSON protocol line.",
                ) from error
            message_object = _object(message, check=check, label="App-server message")
            if "method" in message_object and "id" in message_object:
                raise RpcFailure(
                    check,
                    "server_request_not_supported",
                    "App-server requested client interaction during a read-only probe.",
                )
            if message_object.get("id") == request_id:
                if "error" in message_object:
                    error_value = _object(
                        message_object["error"], check=check, label="JSON-RPC error"
                    )
                    error_code = error_value.get("code", "unknown")
                    raise RpcFailure(
                        check,
                        "rpc_method_error",
                        f"{method!r} failed with RPC code {error_code}; inspect local diagnostics.",
                    )
                if "result" not in message_object:
                    raise RpcFailure(check, "missing_result", f"{method!r} returned no result.")
                return _object(message_object["result"], check=check, label=f"{method} result")
            notification_method = message_object.get("method")
            if isinstance(notification_method, str):
                self.notifications.append(notification_method)
                continue
            raise RpcFailure(
                check,
                "unexpected_response",
                "App-server returned a response for an unexpected request id.",
            )

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._stdin.close()
        try:
            self._process.wait(timeout=1)
            return
        except subprocess.TimeoutExpired:
            self._process.terminate()
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=2)

    def __enter__(self) -> JsonLineRpcClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


def _start_app_server(
    codex: str,
    root: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
    private_paths: Sequence[Path],
) -> JsonLineRpcClient:
    try:
        process = subprocess.Popen(
            [codex, "app-server", "--listen", "stdio://", "--strict-config"],
            cwd=root,
            env=dict(environment),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except (OSError, ValueError) as error:
        raise ProbeFailure(
            "app_server_initialize",
            "cannot_start",
            "Codex app-server could not be started.",
        ) from error
    return JsonLineRpcClient(process, timeout_seconds, private_paths)


def _collect_app_server(
    codex: str,
    root: Path,
    environment: Mapping[str, str],
    codex_home: Path,
    timeout_seconds: float,
) -> dict[str, Mapping[str, Any]]:
    with _start_app_server(
        codex,
        root,
        environment,
        timeout_seconds,
        (root, codex_home),
    ) as client:
        initialized = client.request(
            "initialize",
            {
                "clientInfo": {"name": "minius-runtime-probe", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
            check="app_server_initialize",
        )
        client.notify("initialized", {})
        config = client.request(
            "config/read",
            {"cwd": str(root), "includeLayers": True},
            check="runtime_project_config",
        )
        skills = client.request(
            "skills/list",
            {"cwds": [str(root)], "forceReload": True},
            check="repo_skills",
        )
        hooks = client.request(
            "hooks/list",
            {"cwds": [str(root)]},
            check="project_hooks",
        )
        thread = client.request(
            "thread/start",
            {
                "approvalPolicy": "never",
                "cwd": str(root),
                "ephemeral": True,
                "sandbox": "read-only",
            },
            check="thread_start_no_turn",
        )
    return {
        "initialize": initialized,
        "config": config,
        "skills": skills,
        "hooks": hooks,
        "thread": thread,
    }


def _run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
    check: str = "codex_version",
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(environment),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProbeFailure(check, "command_failed", "A probe command failed.") from error


def _codex_version(
    codex: str,
    root: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    completed = _run_command(
        (codex, "--version"),
        cwd=root,
        environment=environment,
        timeout_seconds=timeout_seconds,
        check="codex_version",
    )
    version = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"codex-cli [0-9A-Za-z.+-]+", version):
        raise ProbeFailure(
            "codex_version",
            "unsupported_version_output",
            "Codex --version did not return the expected sanitized version format.",
        )
    return version


def _git_snapshot(
    root: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    top = _run_command(
        ("git", "-C", str(root), "rev-parse", "--show-toplevel"),
        cwd=root,
        environment=environment,
        timeout_seconds=timeout_seconds,
        check="workspace_git_root",
    )
    if top.returncode != 0:
        raise ProbeFailure(
            "workspace_git_root",
            "not_git_repository",
            "The workspace is not an initialized Git repository.",
        )
    try:
        discovered_root = Path(top.stdout.strip()).resolve(strict=True)
    except OSError as error:
        raise ProbeFailure(
            "workspace_git_root",
            "invalid_git_root",
            "Git returned an invalid repository root.",
        ) from error
    if discovered_root != root:
        raise ProbeFailure(
            "workspace_git_root",
            "nested_git_repository",
            "The supplied workspace is not the exact Git repository root.",
        )
    status = _run_command(
        ("git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=root,
        environment=environment,
        timeout_seconds=timeout_seconds,
        check="workspace_git_root",
    )
    if status.returncode != 0:
        raise ProbeFailure(
            "workspace_git_root", "git_status_failed", "Git status could not be read."
        )
    return status.stdout


def _load_static_project_config(root: Path) -> Mapping[str, Any]:
    path = root / ".codex/config.toml"
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ProbeFailure(
            "static_project_config",
            "invalid_toml",
            "Project .codex/config.toml is absent or invalid.",
        ) from error
    expected_values = {
        ("approval_policy",): "on-request",
        ("sandbox_mode",): "workspace-write",
        ("web_search",): "indexed",
        ("project_root_markers",): [".git"],
        ("sandbox_workspace_write", "network_access"): False,
        ("features", "hooks"): True,
        ("features", "multi_agent"): True,
        ("features", "memories"): False,
        ("agents", "max_threads"): 6,
        ("agents", "max_depth"): 1,
    }
    for keys, expected in expected_values.items():
        current: Any = config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current != expected:
            dotted = ".".join(keys)
            raise ProbeFailure(
                "static_project_config",
                "unexpected_config",
                f"Project config value {dotted!r} differs from the runtime contract.",
            )
    return config


def _load_roles(root: Path) -> tuple[str, ...]:
    roles_root = root / ".codex/agents"
    role_paths = sorted(roles_root.glob("*.toml")) if roles_root.is_dir() else []
    inventory = tuple(sorted(path.stem.replace("-", "_") for path in role_paths))
    if inventory != EXPECTED_ROLES:
        raise ProbeFailure(
            "project_roles",
            "role_inventory_mismatch",
            "Project role inventory is not the exact expected set of 10 roles.",
        )
    names: list[str] = []
    for path in role_paths:
        try:
            role = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ProbeFailure(
                "project_roles", "invalid_role_toml", "A project role TOML file is invalid."
            ) from error
        expected_name = path.stem.replace("-", "_")
        if role.get("name") != expected_name:
            raise ProbeFailure(
                "project_roles",
                "role_name_mismatch",
                "A project role name does not match its filename.",
            )
        for key in ("description", "developer_instructions", "sandbox_mode"):
            if not isinstance(role.get(key), str) or not role[key].strip():
                raise ProbeFailure(
                    "project_roles",
                    "invalid_role_contract",
                    f"A project role has an invalid {key!r} field.",
                )
        names.append(expected_name)
    return tuple(sorted(names))


def _validate_initialize(result: Mapping[str, Any], codex_home: Path) -> dict[str, Any]:
    platform_family = result.get("platformFamily")
    platform_os = result.get("platformOs")
    server_home = result.get("codexHome")
    safe_platform = re.compile(r"[a-z0-9_-]{1,32}")
    if (
        not isinstance(platform_family, str)
        or not safe_platform.fullmatch(platform_family)
        or not isinstance(platform_os, str)
        or not safe_platform.fullmatch(platform_os)
    ):
        raise ProbeFailure(
            "app_server_initialize",
            "invalid_initialize_response",
            "App-server omitted platform compatibility fields.",
        )
    if not isinstance(server_home, str):
        raise ProbeFailure(
            "app_server_initialize", "missing_codex_home", "App-server omitted Codex home."
        )
    try:
        if Path(server_home).resolve() != codex_home.resolve():
            raise ProbeFailure(
                "app_server_initialize",
                "isolation_failed",
                "App-server did not use the isolated temporary Codex home.",
            )
    except OSError as error:
        raise ProbeFailure(
            "app_server_initialize",
            "invalid_codex_home",
            "App-server returned an invalid Codex home.",
        ) from error
    return {"platform_family": platform_family, "platform_os": platform_os}


def _project_layer(config_result: Mapping[str, Any], root: Path) -> Mapping[str, Any]:
    layers = config_result.get("layers")
    if not isinstance(layers, list):
        raise ProbeFailure(
            "runtime_project_config",
            "layers_unavailable",
            "Codex config/read did not expose configuration layers.",
        )
    expected_folder = (root / ".codex").resolve()
    for layer_value in layers:
        if not isinstance(layer_value, dict):
            continue
        name = layer_value.get("name")
        if not isinstance(name, dict) or name.get("type") != "project":
            continue
        folder = name.get("dotCodexFolder")
        if isinstance(folder, str) and Path(folder).resolve() == expected_folder:
            return layer_value
    raise ProbeFailure(
        "runtime_project_config",
        "project_layer_not_loaded",
        "Codex did not load the workspace project config layer.",
    )


def _validate_runtime_config(config_result: Mapping[str, Any], root: Path) -> dict[str, Any]:
    _project_layer(config_result, root)
    config = _object(
        config_result.get("config"), check="runtime_project_config", label="Effective config"
    )
    expected_values = {
        ("approval_policy",): "on-request",
        ("sandbox_mode",): "workspace-write",
        ("web_search",): "indexed",
        ("project_root_markers",): [".git"],
        ("sandbox_workspace_write", "network_access"): False,
        ("features", "multi_agent"): True,
        ("features", "memories"): False,
        ("agents", "max_threads"): 6,
        ("agents", "max_depth"): 1,
    }
    for keys, expected in expected_values.items():
        current: Any = config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current != expected:
            raise ProbeFailure(
                "runtime_project_config",
                "effective_config_mismatch",
                f"Effective project config value {'.'.join(keys)!r} was not applied.",
            )
    return {"source": ".codex/config.toml", "project_layer_loaded": True}


def _cwd_entry(result: Mapping[str, Any], root: Path, check: str) -> Mapping[str, Any]:
    data = result.get("data")
    if not isinstance(data, list):
        raise ProbeFailure(check, "invalid_response", "Codex list response has no data array.")
    for entry_value in data:
        if not isinstance(entry_value, dict):
            continue
        cwd = entry_value.get("cwd")
        if isinstance(cwd, str) and Path(cwd).resolve() == root:
            return entry_value
    raise ProbeFailure(check, "cwd_missing", "Codex list response omitted the requested workspace.")


def _validate_skills(result: Mapping[str, Any], root: Path) -> dict[str, Any]:
    entry = _cwd_entry(result, root, "repo_skills")
    errors = entry.get("errors")
    if not isinstance(errors, list) or errors:
        raise ProbeFailure(
            "repo_skills", "skill_load_errors", "Codex reported one or more skill load errors."
        )
    skills = entry.get("skills")
    if not isinstance(skills, list):
        raise ProbeFailure("repo_skills", "invalid_response", "Codex returned no skills array.")
    repo_skills = [
        item for item in skills if isinstance(item, dict) and item.get("scope") == "repo"
    ]
    names = tuple(sorted(str(item.get("name")) for item in repo_skills))
    if names != EXPECTED_SKILLS:
        raise ProbeFailure(
            "repo_skills",
            "skill_inventory_mismatch",
            "Codex did not discover the exact expected set of 12 repository skills.",
        )
    for skill in repo_skills:
        name = str(skill["name"])
        expected_path = (root / ".agents/skills" / name / "SKILL.md").resolve()
        path = skill.get("path")
        description = skill.get("description")
        if (
            skill.get("enabled") is not True
            or not isinstance(path, str)
            or Path(path).resolve() != expected_path
            or not isinstance(description, str)
            or not description.strip()
        ):
            raise ProbeFailure(
                "repo_skills",
                "invalid_skill_metadata",
                "A discovered repository skill has invalid runtime metadata.",
            )
    return {"count": len(names), "names": list(names)}


def _validate_hooks(result: Mapping[str, Any], root: Path) -> dict[str, Any]:
    entry = _cwd_entry(result, root, "project_hooks")
    errors = entry.get("errors")
    if not isinstance(errors, list) or errors:
        raise ProbeFailure(
            "project_hooks", "hook_load_errors", "Codex reported one or more hook load errors."
        )
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        raise ProbeFailure("project_hooks", "invalid_response", "Codex returned no hooks array.")
    project_hooks = [
        item for item in hooks if isinstance(item, dict) and item.get("source") == "project"
    ]
    events = tuple(sorted(str(item.get("eventName")) for item in project_hooks))
    if events != EXPECTED_HOOK_EVENTS:
        raise ProbeFailure(
            "project_hooks",
            "hook_inventory_mismatch",
            "Codex did not discover exactly the SessionStart and Stop project hooks.",
        )
    expected_source = (root / ".codex/hooks.json").resolve()
    trust_statuses: set[str] = set()
    for hook in project_hooks:
        source_path = hook.get("sourcePath")
        trust_status = hook.get("trustStatus")
        if (
            hook.get("enabled") is not True
            or hook.get("handlerType") != "command"
            or not isinstance(source_path, str)
            or Path(source_path).resolve() != expected_source
            or trust_status not in {"managed", "modified", "trusted", "untrusted"}
        ):
            raise ProbeFailure(
                "project_hooks",
                "invalid_hook_metadata",
                "A discovered project hook has invalid runtime metadata.",
            )
        trust_statuses.add(str(trust_status))
    return {
        "count": len(events),
        "events": list(events),
        "trust_statuses": sorted(trust_statuses),
    }


def _validate_thread(
    result: Mapping[str, Any], root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    thread = _object(result.get("thread"), check="thread_start_no_turn", label="Thread")
    turns = thread.get("turns")
    status = thread.get("status")
    sandbox = result.get("sandbox")
    if (
        thread.get("ephemeral") is not True
        or turns != []
        or not isinstance(status, dict)
        or status.get("type") != "idle"
        or result.get("approvalPolicy") != "never"
        or not isinstance(sandbox, dict)
        or sandbox.get("type") != "readOnly"
        or sandbox.get("networkAccess") is not False
    ):
        raise ProbeFailure(
            "thread_start_no_turn",
            "unsafe_thread_contract",
            "The no-turn thread was not idle, ephemeral, read-only, and network-disabled.",
        )
    cwd = result.get("cwd")
    if not isinstance(cwd, str) or Path(cwd).resolve() != root:
        raise ProbeFailure(
            "thread_start_no_turn", "cwd_mismatch", "Thread started outside the workspace root."
        )
    instruction_sources = result.get("instructionSources")
    if not isinstance(instruction_sources, list):
        raise ProbeFailure(
            "runtime_agents", "instruction_sources_missing", "Thread omitted instruction sources."
        )
    expected_agents = (root / "AGENTS.md").resolve()
    loaded = {Path(value).resolve() for value in instruction_sources if isinstance(value, str)}
    if expected_agents not in loaded:
        raise ProbeFailure(
            "runtime_agents",
            "agents_not_loaded",
            "Codex did not load the workspace AGENTS.md instruction source.",
        )
    thread_evidence = {
        "approval_policy": "never",
        "ephemeral": True,
        "network_access": False,
        "sandbox": "readOnly",
        "turn_count": 0,
    }
    agents_evidence = {"instruction_source": "AGENTS.md"}
    return thread_evidence, agents_evidence


def _evaluate_execpolicy(
    codex: str,
    root: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> dict[str, str]:
    rules_path = root / ".codex/rules/default.rules"
    if not rules_path.is_file():
        raise ProbeFailure("execpolicy", "rules_missing", "Project execpolicy rules are absent.")
    decisions: dict[str, str] = {}
    for label, command, expected in RULE_CASES:
        try:
            completed = runner(
                (
                    codex,
                    "execpolicy",
                    "check",
                    "--pretty",
                    "--rules",
                    str(rules_path),
                    "--",
                    *command,
                ),
                cwd=root,
                environment=environment,
                timeout_seconds=timeout_seconds,
                check="execpolicy",
            )
        except ProbeFailure as error:
            raise ProbeFailure(
                "execpolicy",
                "execpolicy_unavailable",
                "Codex execpolicy check is unavailable or timed out.",
            ) from error
        if completed.returncode != 0:
            raise ProbeFailure(
                "execpolicy",
                "execpolicy_failed",
                "Codex execpolicy check returned a non-zero status.",
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ProbeFailure(
                "execpolicy",
                "invalid_execpolicy_json",
                "Codex execpolicy check did not return JSON.",
            ) from error
        payload_object = _object(payload, check="execpolicy", label="Execpolicy result")
        decision = payload_object.get("decision")
        if decision != expected:
            raise ProbeFailure(
                "execpolicy",
                "decision_mismatch",
                f"Execpolicy case {label!r} returned an unexpected decision.",
            )
        decisions[label] = str(decision)
    return decisions


def _record_pass(result: dict[str, Any], check: str, evidence: Mapping[str, Any]) -> None:
    result["checks"][check] = {"status": "PASS", **evidence}


def _record_failure(
    result: dict[str, Any],
    error: ProbeFailure,
    private_paths: Sequence[Path],
) -> None:
    result["checks"][error.check] = {"status": "FAIL", "code": error.code}
    result["diagnostics"].append(
        {
            "check": error.check,
            "code": error.code,
            "message": _sanitize_message(str(error), private_paths),
        }
    )


def _base_result() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "probe": "minius-codex-runtime-compatibility",
        "status": "FAIL",
        "codex_version": None,
        "checks": {check: {"status": "NOT_RUN"} for check in REQUIRED_CHECKS},
        "diagnostics": [],
        "limitations": [
            "No model turn or network-transfer command is executed.",
            (
                "Hooks are discovered in an isolated Codex home; this probe does not trust or "
                "execute them."
            ),
            (
                "The app-server protocol exposes no project-role list; role TOML inventory is "
                "validated while the project multi-agent config layer is runtime-confirmed."
            ),
        ],
    }


def run_probe(codex: str, root_value: Path, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Run the compatibility probe and return a sanitized JSON-serializable result."""

    result = _base_result()
    try:
        root = root_value.resolve(strict=True)
    except OSError:
        error = ProbeFailure("workspace_git_root", "root_missing", "Workspace root is absent.")
        _record_failure(result, error, (root_value,))
        return result
    if not root.is_dir():
        error = ProbeFailure(
            "workspace_git_root", "root_not_directory", "Workspace root is not a directory."
        )
        _record_failure(result, error, (root,))
        return result
    if not 1 <= timeout_seconds <= 60:
        error = ProbeFailure(
            "app_server_initialize",
            "invalid_timeout",
            "Timeout must be between 1 and 60 seconds.",
        )
        _record_failure(result, error, (root,))
        return result

    with tempfile.TemporaryDirectory(prefix="minius-codex-probe-") as temporary:
        codex_home = Path(temporary).resolve()
        trust_config = f'[projects.{_toml_string(str(root))}]\ntrust_level = "trusted"\n'
        (codex_home / "config.toml").write_text(trust_config, encoding="utf-8")
        environment = _isolated_environment(codex_home)
        private_paths = (root, codex_home)

        try:
            version = _codex_version(codex, root, environment, timeout_seconds)
            result["codex_version"] = version
            _record_pass(result, "codex_version", {})
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)
            return result

        initial_snapshot: str | None = None
        try:
            initial_snapshot = _git_snapshot(root, environment, timeout_seconds)
            _record_pass(result, "workspace_git_root", {"exact_root": True})
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)
            return result

        try:
            _load_static_project_config(root)
            _record_pass(result, "static_project_config", {"source": ".codex/config.toml"})
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)

        try:
            roles = _load_roles(root)
            _record_pass(
                result,
                "project_roles",
                {
                    "count": len(roles),
                    "names": list(roles),
                    "verification_method": "static_toml_inventory",
                },
            )
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)

        app_data: dict[str, Mapping[str, Any]] | None = None
        try:
            app_data = _collect_app_server(codex, root, environment, codex_home, timeout_seconds)
            initialize_evidence = _validate_initialize(app_data["initialize"], codex_home)
            _record_pass(result, "app_server_initialize", initialize_evidence)
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)

        if app_data is not None:
            try:
                evidence = _validate_runtime_config(app_data["config"], root)
                _record_pass(result, "runtime_project_config", evidence)
            except ProbeFailure as error:
                _record_failure(result, error, private_paths)
            try:
                evidence = _validate_skills(app_data["skills"], root)
                _record_pass(result, "repo_skills", evidence)
            except ProbeFailure as error:
                _record_failure(result, error, private_paths)
            try:
                evidence = _validate_hooks(app_data["hooks"], root)
                _record_pass(result, "project_hooks", evidence)
            except ProbeFailure as error:
                _record_failure(result, error, private_paths)
            try:
                thread_evidence, agents_evidence = _validate_thread(app_data["thread"], root)
                _record_pass(result, "thread_start_no_turn", thread_evidence)
                _record_pass(result, "runtime_agents", agents_evidence)
            except ProbeFailure as error:
                _record_failure(result, error, private_paths)

        try:
            decisions = _evaluate_execpolicy(codex, root, environment, timeout_seconds)
            _record_pass(result, "execpolicy", {"decisions": decisions})
        except ProbeFailure as error:
            _record_failure(result, error, private_paths)

        try:
            final_snapshot = _git_snapshot(root, environment, timeout_seconds)
            if final_snapshot != initial_snapshot:
                raise ProbeFailure(
                    "workspace_unchanged",
                    "git_status_changed",
                    "Workspace Git status changed while the read-only probe was running.",
                )
            _record_pass(result, "workspace_unchanged", {"git_status_unchanged": True})
        except ProbeFailure as error:
            if error.check == "workspace_git_root":
                error = ProbeFailure("workspace_unchanged", error.code, str(error))
            _record_failure(result, error, private_paths)

    if all(result["checks"][check]["status"] == "PASS" for check in REQUIRED_CHECKS):
        result["status"] = "PASS"
    return result


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Minius Codex runtime discovery without running a model turn or an "
            "evaluated command."
        )
    )
    parser.add_argument("--codex", required=True, help="Codex executable path or command name.")
    parser.add_argument("--root", required=True, type=Path, help="Initialized workspace Git root.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=15.0,
        help="Per-operation timeout from 1 to 60 seconds (default: 15).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_probe(args.codex, args.root, args.timeout_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
