from __future__ import annotations

from typing import Any

from ..client import Miosa
from ..types import ExecResult
from .types import Tool


def miosa_tools(
    client: Miosa,
    *,
    sandbox_template: str = "debian-12-sandbox-v8",
    computer_template: str = "miosa-desktop",
    default_size: str = "small",
    allow_destroy: bool = True,
) -> list[Tool]:
    """Build the default agent-facing MIOSA tool catalogue."""

    def create_sandbox(args: dict[str, Any]) -> str:
        computer = client.computers.create(
            str(args.get("name") or "agent-sandbox"),
            template_type=sandbox_template,
            size=str(args.get("size") or default_size),
        )
        return (
            f"Created sandbox id={computer.id} status={computer.status} "
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

    def exec_bash(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        result = computer.bash(str(args.get("command") or ""), timeout=_timeout(args))
        return _format_exec(result)

    def exec_python(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        result = computer.python(str(args.get("code") or ""), timeout=_timeout(args))
        return _format_exec(result)

    def read_file(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        return computer.read_file(str(args.get("path") or ""))

    def write_file(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        computer.write_file(path, content)
        return f"Wrote {len(content)} bytes to {path}."

    def list_files(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        path = str(args.get("path") or "/workspace")
        result = computer.bash(f"ls -la {_shell_quote(path)}", timeout=10)
        return _format_exec(result)

    def preview_url(args: dict[str, Any]) -> str:
        computer = client.computers.get(_computer_id(args))
        port = int(args.get("port") or 0)
        path = str(args.get("path") or "/")
        return computer.preview_url(port, path)

    tools = [
        Tool(
            "create_sandbox",
            "Boot a fast MIOSA code sandbox computer for Python, Node, shell, "
            "tests, files, and build work.",
            _schema(
                {
                    "name": {"type": "string"},
                    "size": {"type": "string", "enum": ["small", "medium", "large", "xlarge"]},
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
                    "size": {"type": "string", "enum": ["small", "medium", "large", "xlarge"]},
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
            "Run a bash command inside a MIOSA computer/sandbox. Use after "
            "the computer is running.",
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
