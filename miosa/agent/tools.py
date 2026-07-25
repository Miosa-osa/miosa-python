from __future__ import annotations

from typing import Any

from ..client import Miosa
from ..types import ExecResult
from .types import Tool


def miosa_tools(
    client: Miosa,
    *,
    sandbox_template: str = "miosa-sandbox",
    computer_template: str = "miosa-desktop",
    default_size: str = "small",
    workspace_timeout_sec: int = 86_400,
    idle_timeout_sec: int = 1800,
    allow_destroy: bool = True,
) -> list[Tool]:
    """Build the default agent-facing MIOSA tool catalogue."""

    def create_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.create_agent_workspace(
            str(args.get("name") or "agent-sandbox"),
            template_id=sandbox_template,
            timeout_sec=workspace_timeout_sec,
            idle_timeout_sec=idle_timeout_sec,
        )
        return (
            f"Sandbox workspace id={sandbox.id} state={sandbox.state} "
            f"template={sandbox_template}."
        )

    def create_computer(args: dict[str, Any]) -> str:
        template = str(args.get("template_type") or computer_template)
        computer = client.computers.create(
            str(args.get("name") or "agent-computer"),
            template_type=template,
            size=str(args.get("size") or default_size),
        )
        return f"Created computer id={computer.id} status={computer.status} template={template}."

    def list_computers(_: dict[str, Any]) -> str:
        computers = client.computers.list()
        if not computers:
            return "No computers."
        return "\n".join(
            f"{computer.id}  {computer.status}  {computer.data.template_type}  {computer.name}"
            for computer in computers
        )

    def get_computer(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        return (
            f"id={computer.id} status={computer.status} "
            f"template={computer.data.template_type} size={computer.data.size} "
            f"public_url={computer.public_url}"
        )

    def destroy_computer(args: dict[str, Any]) -> str:
        computer_id = _computer_id(args)
        client.computers.delete(computer_id)
        return f"Destroyed {computer_id}."

    def pause_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        sandbox.pause()
        return f"Paused sandbox {sandbox.id}."

    def resume_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        sandbox.resume()
        return f"Resumed sandbox {sandbox.id}."

    def extend_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        timeout_sec = int(args.get("timeout_sec") or 86_400)
        sandbox.extend(timeout_sec)
        return f"Extended sandbox {sandbox.id} timeout to {timeout_sec}s."

    def snapshot_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        comment = str(args.get("comment") or "agent checkpoint")
        snap = sandbox.create_snapshot(comment)
        return f"Snapshot created: {snap.get('id') or snap.get('snapshot_id') or snap}"

    def exec_bash(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        if target["kind"] == "sandbox":
            result = target["value"].exec.run(
                str(args.get("command") or ""),
                {"timeout_sec": _timeout(args)} if _timeout(args) else None,
            )
        else:
            result = target["value"].bash(str(args.get("command") or ""), timeout=_timeout(args))
        return _format_exec(result)

    def exec_python(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        code = str(args.get("code") or "")
        if target["kind"] == "sandbox":
            result = target["value"].exec.run(
                f"python3 - <<'PY'\n{code}\nPY",
                {"timeout_sec": _timeout(args)} if _timeout(args) else None,
            )
        else:
            result = target["value"].python(code, timeout=_timeout(args))
        return _format_exec(result)

    def read_file(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        path = str(args.get("path") or "")
        if target["kind"] == "sandbox":
            return str(target["value"].files.read_text(path))
        return target["value"].read_file(path)

    def write_file(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        if target["kind"] == "sandbox":
            target["value"].files.write(path, content)
        else:
            target["value"].write_file(path, content)
        return f"Wrote {len(content)} bytes to {path}."

    def list_files(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        path = str(args.get("path") or "/workspace")
        if target["kind"] == "sandbox":
            result = target["value"].exec.run(f"ls -la {_shell_quote(path)}", {"timeout_sec": 10})
        else:
            result = target["value"].bash(f"ls -la {_shell_quote(path)}", timeout=10)
        return _format_exec(result)

    def preview_url(args: dict[str, Any]) -> str:
        target = _get_target(client, _computer_id(args))
        port = int(args.get("port") or 0)
        path = str(args.get("path") or "/")
        if target["kind"] == "sandbox":
            preview = target["value"].preview.create(port=port, path=path)
            return str(preview.get("url") or preview.get("preview_url") or "")
        return target["value"].preview_url(port, path)

    def deploy_sandbox(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        result = sandbox.deploy(
            name=str(args.get("name") or ""),
            path=str(args.get("path") or "/workspace"),
            build_command=str(args["build_command"]) if args.get("build_command") else None,
            run_command=str(args["run_command"]) if args.get("run_command") else None,
            port=int(args["port"]) if args.get("port") else None,
        )
        return str(result)

    def deploy_docker(args: dict[str, Any]) -> str:
        sandbox = client.sandboxes.get(_computer_id(args))
        result = sandbox.deploy_docker(
            name=str(args.get("name") or ""),
            path=str(args.get("path") or "/workspace"),
            build_command=str(args["build_command"]) if args.get("build_command") else None,
            run_command=str(args["run_command"]) if args.get("run_command") else None,
            port=int(args["port"]) if args.get("port") else None,
        )
        return str(result)

    tools = [
        Tool(
            "create_sandbox",
            "Create or resume a persistent MIOSA sandbox workspace for Python, "
            "Node, shell, tests, files, artifacts, dev servers, and build work. "
            "Work inside /workspace.",
            _schema(
                {
                    "name": {"type": "string"},
                    "size": {"type": "string", "enum": ["xs", "small", "medium", "large", "xl", "xlarge"]},
                },
                ["name"],
            ),
            create_sandbox,
        ),
        Tool(
            "create_computer",
            "Boot a general MIOSA computer for GUI, services, previews, "
            "browser work, files, and terminals.",
            _schema(
                {
                    "name": {"type": "string"},
                    "template_type": {"type": "string"},
                    "size": {"type": "string", "enum": ["xs", "small", "medium", "large", "xl", "xlarge"]},
                },
                ["name"],
            ),
            create_computer,
        ),
        Tool(
            "list_computers",
            "List active MIOSA computers/sandboxes/desktops.",
            _schema({}),
            list_computers,
        ),
        Tool(
            "get_computer",
            "Fetch one MIOSA computer by id and show status/template/preview.",
            _id_schema(),
            get_computer,
        ),
        Tool(
            "exec",
            "Run a bash command inside a MIOSA sandbox workspace or computer. "
            "Use after the sandbox is running.",
            _schema(
                {
                    "computer_id": {"type": "string"},
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 300},
                },
                ["computer_id", "command"],
            ),
            exec_bash,
        ),
        Tool(
            "exec_python",
            "Run a Python snippet inside a MIOSA computer/sandbox.",
            _schema(
                {
                    "computer_id": {"type": "string"},
                    "code": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 300},
                },
                ["computer_id", "code"],
            ),
            exec_python,
        ),
        Tool(
            "read_file",
            "Read UTF-8 text from a file inside the computer.",
            _path_schema(),
            read_file,
        ),
        Tool(
            "write_file",
            "Write UTF-8 text to a file inside the computer, overwriting if present.",
            _schema(
                {
                    "computer_id": {"type": "string"},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                ["computer_id", "path", "content"],
            ),
            write_file,
        ),
        Tool(
            "list_files",
            "List a directory inside the computer using ls -la.",
            _schema(
                {"computer_id": {"type": "string"}, "path": {"type": "string"}},
                ["computer_id"],
            ),
            list_files,
        ),
        Tool(
            "preview_url",
            "Return the public HTTPS preview URL for a service running on a computer port.",
            _schema(
                {
                    "computer_id": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "path": {"type": "string"},
                },
                ["computer_id", "port"],
            ),
            preview_url,
        ),
        Tool(
            "pause_sandbox",
            "Pause a persistent sandbox workspace while preserving its filesystem.",
            _id_schema(),
            pause_sandbox,
        ),
        Tool(
            "resume_sandbox",
            "Resume a paused persistent sandbox workspace.",
            _id_schema(),
            resume_sandbox,
        ),
        Tool(
            "extend_sandbox",
            "Extend a running sandbox workspace before a long install, build, or agent task.",
            _schema(
                {
                    "computer_id": {"type": "string"},
                    "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 86400},
                },
                ["computer_id"],
            ),
            extend_sandbox,
        ),
        Tool(
            "snapshot_sandbox",
            "Create a checkpoint snapshot for a sandbox workspace.",
            _schema(
                {"computer_id": {"type": "string"}, "comment": {"type": "string"}},
                ["computer_id"],
            ),
            snapshot_sandbox,
        ),
        Tool(
            "deploy_sandbox",
            "Publish a sandbox workspace to a durable MIOSA deployment after preview tests pass.",
            _deploy_schema(),
            deploy_sandbox,
        ),
        Tool(
            "deploy_docker",
            "Publish a sandbox workspace through the workspace App Engine appliance.",
            _deploy_schema(),
            deploy_docker,
        ),
    ]
    if allow_destroy:
        tools.append(
            Tool(
                "destroy_computer",
                "Destroy a MIOSA computer/sandbox/desktop and release resources.",
                _id_schema(),
                destroy_computer,
            )
        )
    return tools


def _computer_id(args: dict[str, Any]) -> str:
    return str(args.get("computer_id") or args.get("sandbox_id") or "")


def _timeout(args: dict[str, Any]) -> int | None:
    value = args.get("timeout")
    return int(value) if value is not None else None


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def _id_schema() -> dict[str, Any]:
    return _schema({"computer_id": {"type": "string"}}, ["computer_id"])


def _path_schema() -> dict[str, Any]:
    return _schema(
        {"computer_id": {"type": "string"}, "path": {"type": "string"}},
        ["computer_id", "path"],
    )


def _deploy_schema() -> dict[str, Any]:
    return _schema(
        {
            "computer_id": {"type": "string"},
            "name": {"type": "string"},
            "path": {"type": "string"},
            "build_command": {"type": "string"},
            "run_command": {"type": "string"},
            "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        },
        ["computer_id", "name"],
    )


def _get_target(client: Miosa, target_id: str) -> dict[str, Any]:
    try:
        return {"kind": "sandbox", "value": client.sandboxes.get(target_id)}
    except Exception:
        return {"kind": "computer", "value": client.computers.get(target_id)}


def _format_exec(result: ExecResult) -> str:
    parts: list[str] = []
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr}")
    parts.append(f"exit_code: {result.exit_code}")
    return "\n".join(parts)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
