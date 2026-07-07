"""命令执行工具。"""

from tool.registry import registry

BASH_SCHEMA = {
    "name": "bash",
    "description": "执行 shell 命令，返回输出结果",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令",
            },
            "timeout": {
                "type": "integer",
                "description": "超时秒数，默认 30",
            },
        },
        "required": ["command"],
    },
}

BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", "rm -rf .", "del /f /s", "format",
    "shutdown", "reboot", "init 0", "poweroff",
]


def bash_handler(args):
    import subprocess
    from config.settings import get_work_dir

    command = args["command"]
    timeout = args.get("timeout", 30)

    result = subprocess.run(
        command,
        shell=True,
        cwd=str(get_work_dir()),
        capture_output=True,
        text=True,
        timeout=timeout,
        )
    
    output = result.stdout
    if result.stderr:
        output += "\n" +result.stderr

    return {
        "success": result.returncode == 0,
        "output": output.strip(),
        "returncode": result.returncode,
    }


registry.register(
    name="bash",
    handler=bash_handler,
    schema=BASH_SCHEMA,
)
