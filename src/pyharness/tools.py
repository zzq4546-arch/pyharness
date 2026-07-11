import os
import subprocess
from pyharness.models import Action, ToolResult
from pyharness.config import ConfigLoader


class ToolExecutor:
    def __init__(self, config: ConfigLoader, workspace: str):
        self._config = config
        self._workspace = workspace

    def execute(self, action: Action) -> ToolResult:
        enabled = self._config.get("tools.enabled", [])
        if action.tool_name not in enabled:
            return ToolResult(
                tool_name=action.tool_name,
                success=False,
                output="",
                error=f"Tool '{action.tool_name}' is disabled",
            )

        handler = getattr(self, f"_handle_{action.tool_name}", None)
        if handler is None:
            return ToolResult(
                tool_name=action.tool_name,
                success=False,
                output="",
                error=f"Unknown tool: {action.tool_name}",
            )
        return handler(action.tool_args or {})

    def _handle_read_file(self, args: dict) -> ToolResult:
        path = args.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(tool_name="read_file", success=True, output=content)
        except Exception as e:
            return ToolResult(tool_name="read_file", success=False, output="", error=str(e))

    def _handle_write_file(self, args: dict) -> ToolResult:
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(tool_name="write_file", success=True, output=f"Written to {path}")
        except Exception as e:
            return ToolResult(tool_name="write_file", success=False, output="", error=str(e))

    def _handle_execute_shell(self, args: dict) -> ToolResult:
        command = args.get("command", "")
        timeout = self._config.get("tool_timeout", 60)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self._workspace,
            )
            return ToolResult(
                tool_name="execute_shell",
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name="execute_shell",
                success=False, output="",
                error=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(tool_name="execute_shell", success=False, output="", error=str(e))

    def _handle_run_tests(self, args: dict) -> ToolResult:
        command = args.get("command", "pytest")
        return self._handle_execute_shell({"command": command})

    def _handle_run_lint(self, args: dict) -> ToolResult:
        target = args.get("path", ".")
        command = f"ruff check {target}" if args.get("path") else "ruff check ."
        return self._handle_execute_shell({"command": command})

    def _handle_list_files(self, args: dict) -> ToolResult:
        path = args.get("path", self._workspace)
        try:
            entries = os.listdir(path)
            lines = []
            for entry in sorted(entries):
                full = os.path.join(path, entry)
                suffix = "/" if os.path.isdir(full) else ""
                lines.append(entry + suffix)
            return ToolResult(tool_name="list_files", success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(tool_name="list_files", success=False, output="", error=str(e))