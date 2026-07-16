"""命令执行工具 — 支持中断轮询。"""

import subprocess
import time

from tool.registry import registry
from tool import cancel

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

_POLL_INTERVAL = 0.3  # 每 300ms 检查一次取消标志
_current_proc: subprocess.Popen | None = None


def cancel_current():
    global _current_proc
    if _current_proc:
        try:
            _current_proc.kill()
        except Exception:
            pass


def is_running() -> bool:
    return _current_proc is not None


def bash_handler(args):
    from config.settings import get_work_dir

    command = args["command"]
    timeout = args.get("timeout", 30)

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=str(get_work_dir()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    global _current_proc
    _current_proc = process

    stdout_lines = []
    stderr_lines = []
    start = time.time()

    # 逐行读取 stdout，同时轮询取消标志
    while True:
        if cancel.is_requested():
            process.kill()
            process.wait()
            _current_proc = None
            return {
                "success": False,
                "output": "[interrupted]",
                "returncode": -1,
            }

        # 读一行（非阻塞 + 短超时）
        line = process.stdout.readline()
        if line:
            stdout_lines.append(line)
        else:
            # stdout 读完了，检查进程是否结束
            ret = process.poll()
            if ret is not None:
                break

        # 超时检查
        if time.time() - start > timeout:
            process.kill()
            process.wait()
            _current_proc = None
            return {
                "success": False,
                "output": "".join(stdout_lines) + "\n[timeout]",
                "returncode": -1,
            }

        time.sleep(_POLL_INTERVAL)

    # 收集剩余 stderr
    stderr_lines = process.stderr.readlines()

    output = "".join(stdout_lines)
    if stderr_lines:
        output += "\n" + "".join(stderr_lines)

    _current_proc = None
    return {
        "success": process.returncode == 0,
        "output": output.strip(),
        "returncode": process.returncode,
    }


registry.register(
    name="bash",
    handler=bash_handler,
    schema=BASH_SCHEMA,
)
