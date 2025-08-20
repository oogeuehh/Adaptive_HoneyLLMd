# llm_shell.py (完整实现)
# 集成了：
# - 你提供的 Robust split_commands / parse_command
# - HPA 阻断判断（来自 hpa_manager.HPA 与 blocker.should_block）
# - 本地内置命令模拟（uname/ls/cat/cd/pwd/echo/exit/whoami 等）
# - 当未命中本地模拟时回退到 LLM
#
# 使用方法：通过环境变量配置 LLM 与 HPA 路径等
#   LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, HPA_JSON_PATH, PAYOFF_THRESHOLD, MIN_STEPS_BEFORE_BLOCK, LLM_SHELL_PORT

import os
import json
import sys
import requests
from openai import OpenAI
from flask import Flask, request
from hpa_manager import HPA, HPA_DEFAULT_PATH
from blocker import should_block

# Config from env
API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.chatanywhere.tech")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

HPA_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")
try:
    hpa = HPA(HPA_PATH)
except Exception:
    hpa = HPA()  # fallback

# session_id -> list[(macro,micro)]
session_paths = {}

# --- LLM wrapper ---
def get_response_from_llm(message: str) -> str:
    if not API_KEY:
        print("Warning: LLM_API_KEY not set", file=sys.stderr)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a shell with system information Linux svr04 3.2.0-4-amd64 #1 SMP Debian 3.2.68-1+deb7u1 "
                "x86_64 GNU/Linux with distribution Debian GNU/Linux 8.11 (jessie). Now you need to simulate a bash shell, "
                "your output should look as if you executed the command, and you should not output any other text that is not part of the response of this command."
            ),
        },
        {"role": "user", "content": message},
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        print("LLM error:", e, file=sys.stderr)
        return None

# --- Robust command splitting & parsing (来自你提供的实现) ---

def split_commands(cmd: str):
    """Split a complex shell command string into sub-commands while respecting quotes, braces, &&, ||, ; and |.
    Returns list of sub-commands (strings).
    """
    result = []
    current = ''
    i = 0
    length = len(cmd)
    in_single_quote = False
    in_double_quote = False
    brace_level = 0
    while i < length:
        char = cmd[i]
        # quote state judgement
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current += char
            i += 1
            continue
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current += char
            i += 1
            continue
        elif char == '{' and not in_single_quote and not in_double_quote:
            brace_level += 1
            current += char
            i += 1
            continue
        elif char == '}' and not in_single_quote and not in_double_quote:
            brace_level = max(0, brace_level - 1)
            current += char
            i += 1
            continue

        # only treat separators when not inside quotes or braces
        if not in_single_quote and not in_double_quote and brace_level == 0:
            # &&
            if cmd[i:i+2] == '&&':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            # ||
            if cmd[i:i+2] == '||':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            # ; or |
            if char in [';', '|']:
                result.append(current.strip())
                current = ''
                i += 1
                continue
        # accumulate
        current += char
        i += 1
    if current.strip():
        result.append(current.strip())
    return result


def parse_command(cmd: str):
    """Parse a sub-command into (macro, micro). Returns tuple (macro, micro) where micro is 'none' if absent."""
    if not cmd or not cmd.strip():
        return "unknown", "none"
    # remove surrounding parentheses (common in subshells)
    s = cmd.strip()
    while s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()
    # split on first whitespace to get macro and micro
    parts = s.split(None, 1)
    macro = parts[0]
    micro = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "none"
    return macro, micro

# --- Local simulated commands (keep behavior from your original file) ---

def run_command_local(command: str) -> str:
    command = command.strip()
    if not command:
        return "\n"
    if command == "uname -a":
        return "Linux svr04 3.2.0-4-amd64 #1 SMP Debian 3.2.68-1+deb7u1 x86_64 GNU/Linux\n"
    if command == "lsb_release -a":
        return ("No LSB modules are available.\n"
                "Distributor ID: Debian\n"
                "Description: Debian GNU/Linux 8.11 (jessie)\n"
                "Release: 8.11\n"
                "Codename: jessie\n")
    if command == "dpkg --get-selections":
        return ("adduser install\n"
                "apt install\n"
                "base-files install\n"
                "base-passwd install\n"
                "bash install\n"
                "bsdutils install\n"
                "coreutils install\n")
    if command == "service --status-all":
        return ("[ + ] acpid\n"
                "[ + ] cron\n"
                "[ + ] dbus\n"
                "[ + ] exim4\n"
                "[ + ] kmod\n"
                "[ + ] networking\n"
                "[ + ] rsyslog\n"
                "[ + ] ssh\n"
                "[ + ] udev\n"
                "[ - ] procps\n")
    if command.startswith("cat"):
        parts = command.split(None, 1)
        if len(parts) == 1:
            return "cat: : No such file or directory\n"
        filename = parts[1].strip()
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except FileNotFoundError:
            return f"cat: {filename}: No such file or directory\n"
        except Exception:
            return f"cat: {filename}: No such file or directory\n"
    if command.startswith("ls"):
        parts = command.split(None, 1)
        path = '.'
        if len(parts) > 1:
            path = parts[1].strip()
        try:
            return " ".join(os.listdir(path)) + "\n"
        except Exception:
            return f"ls: cannot access {path}: No such file or directory\n"
    if command.startswith("cd"):
        parts = command.split(None, 1)
        if len(parts) == 1:
            path = os.path.expanduser('~')
        else:
            path = parts[1].strip()
        try:
            os.chdir(path)
            return ""
        except FileNotFoundError:
            return f"bash: cd: {path}: No such file or directory\n"
        except NotADirectoryError:
            return f"bash: cd: {path}: Not a directory\n"
    if command == "pwd":
        return f"{os.getcwd()}\n"
    if command.startswith("echo"):
        parts = command.split(None, 1)
        if len(parts) > 1:
            return parts[1] + "\n"
        else:
            return "\n"
    if command == "exit":
        # Don't actually exit the server process; simulate
        return "logout\n"
    if command == "whoami":
        return "root\n"
    # not handled locally
    return None

# --- Block response generator ---
def fake_block_response(command: str):
    # You can make this rotate through a set of plausible errors to avoid detection.
    # Keep it simple here.
    return "bash: permission denied\n"

# --- Flask app ---
app = Flask(__name__)

@app.route('/execute', methods=['GET'])
def execute_command_get():
    command = request.args.get('command', '')
    session = request.args.get('session', 'unknown-session')

    # Split into sub-commands; choose last as "active" (most interactive)
    subs = split_commands(command)
    active = subs[-1] if subs else command

    macro, micro = parse_command(active)

    # maintain session path
    sp = session_paths.setdefault(session, [])
    sp.append((macro, micro))

    # check block decision
    decision, debug = should_block(hpa, session, sp)
    # in production use structured logger rather than print
    print("HPA debug:", json.dumps(debug, ensure_ascii=False))

    if decision:
        return fake_block_response(command)

    # not blocked -> try local execution first
    local = run_command_local(command)
    if local is not None:
        return local

    # fallback to LLM
    llm_out = get_response_from_llm(command)
    if llm_out is None:
        # LLM failure -> return plausible command-not-found
        cmd0 = command.split()[0] if command.strip() else ""
        return f"bash: {cmd0}: command not found\n"
    return llm_out + "\n"

if __name__ == '__main__':
    port = int(os.environ.get('LLM_SHELL_PORT', '12345'))
    print(f"Starting llm_shell on 0.0.0.0:{port}")
    app.run(host='127.0.0.1', port=port)
