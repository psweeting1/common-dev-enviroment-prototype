import os
import sys
import time
import subprocess
from typing import List, Optional

def colorize_lightblue(msg: str) -> str:
    return f"\033[36m{msg}\033[0m"

def colorize_red(msg: str) -> str:
    return f"\033[31m{msg}\033[0m"

def colorize_yellow(msg: str) -> str:
    return f"\033[33m{msg}\033[0m"

def colorize_green(msg: str) -> str:
    return f"\033[32m{msg}\033[0m"

def colorize_pink(msg: str) -> str:
    return f"\033[35m{msg}\033[0m"

def run_command(cmd: str, output_lines: Optional[List[str]] = None, input_lines: Optional[str] = None) -> int:
    """
    Runs a shell command, optionally piping input and collecting output.
    """
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if input_lines is not None:
        process.stdin.write(input_lines)
        process.stdin.close()
    for line in process.stdout:
        if output_lines is None:
            print(line, end='')
        else:
            output_lines.append(line.rstrip('\n'))
    process.wait()
    return process.returncode

def run_command_noshell(cmd: List[str], output_lines: Optional[List[str]] = None, input_lines: Optional[str] = None) -> int:
    """
    Runs a command without shell, optionally piping input and collecting output.
    """
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if input_lines is not None:
        process.stdin.write(input_lines)
        process.stdin.close()
    for line in process.stdout:
        if output_lines is None:
            print(line, end='')
        else:
            output_lines.append(line.rstrip('\n'))
    process.wait()
    return process.returncode

def fail_and_exit(new_project: bool, DEV_ENV_CONTEXT_FILE: str, DEV_ENV_CONFIG_DIR: str) -> None:
    print(colorize_red('Something went wrong when cloning/pulling the dev-env configuration project. Check your URL?'))
    if new_project:
        try:
            os.remove(DEV_ENV_CONTEXT_FILE)
        except FileNotFoundError:
            pass
        if os.path.isdir(DEV_ENV_CONFIG_DIR):
            import shutil
            shutil.rmtree(DEV_ENV_CONFIG_DIR)
        sys.exit(1)
    else:
        print(colorize_yellow('Continuing in 3 seconds...'))
        time.sleep(3)

def check_healthy_output(command_output: List[str]) -> bool:
    return any(ln.startswith('"healthy"') for ln in command_output)
