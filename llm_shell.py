# llm_shell_amun.py
import os
import json
import sys
import re
from flask import Flask, request
from openai import OpenAI
from hpa_manager import HPA
from blocker import should_block

API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.chatanywhere.tech")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

HPA_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")
try:
    hpa = HPA(HPA_PATH)
except Exception:
    hpa = HPA()

# session_id -> list[(macro,micro)]
session_paths = {}

# --- LLM wrapper ---
def get_response_from_llm(message: str) -> str:
    if not API_KEY:
        print("Warning: LLM_API_KEY not set", file=sys.stderr)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [
        {"role": "system",
         "content": (
             "You are a shell with system information Linux svr04 3.2.0-4-amd64. "
             "Simulate bash shell output only."
         )},
        {"role": "user", "content": message},
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        print("LLM error:", e, file=sys.stderr)
        return None

# --- Robust command parsing ---
def split_commands(cmd: str):
    result, current, i, in_squote, in_dquote, brace_level = [], '', 0, False, False, 0
    while i < len(cmd):
        c = cmd[i]
        if c == "'" and not in_dquote: in_squote = not in_squote; current += c; i+=1; continue
        if c == '"' and not in_squote: in_dquote = not in_dquote; current += c; i+=1; continue
        if c == '{' and not in_squote and not in_dquote: brace_level += 1; current += c; i+=1; continue
        if c == '}' and not in_squote and not in_dquote: brace_level = max(0, brace_level-1); current+=c;i+=1;continue
        if not in_squote and not in_dquote and brace_level==0:
            if cmd[i:i+2] in ['&&','||']: result.append(current.strip()); current=''; i+=2; continue
            if c in [';', '|']: result.append(current.strip()); current=''; i+=1; continue
        current += c; i+=1
    if current.strip(): result.append(current.strip())
    return result

def parse_command(cmd: str):
    if not cmd.strip(): return "unknown", "none"
    s = cmd.strip()
    while s.startswith('(') and s.endswith(')'): s = s[1:-1].strip()
    parts = s.split(None, 1)
    macro = parts[0]
    micro = parts[1].strip() if len(parts)>1 and parts[1].strip() else "none"
    return macro, micro

# --- Local commands ---
def run_command_local(command: str):
    command = command.strip()
    if not command: return "\n"
    if command == "uname -a": return "Linux svr04 3.2.0-4-amd64 #1 SMP Debian 3.2.68-1+deb7u1 x86_64 GNU/Linux\n"
    if command == "lsb_release -a": return ("No LSB modules are available.\nDistributor ID: Debian\nRelease: 8.11\n")
    if command.startswith("cat"):
        filename = command.split(None,1)[1].strip() if len(command.split(None,1))>1 else ""
        try: return open(filename,'r',encoding='utf-8',errors='ignore').read()
        except: return f"cat: {filename}: No such file or directory\n"
    if command.startswith("ls"):
        path = command.split(None,1)[1].strip() if len(command.split(None,1))>1 else "."
        try: return " ".join(os.listdir(path)) + "\n"
        except: return f"ls: cannot access {path}: No such file or directory\n"
    if command.startswith("cd"):
        path = command.split(None,1)[1].strip() if len(command.split(None,1))>1 else os.path.expanduser('~')
        try: os.chdir(path); return ""
        except FileNotFoundError: return f"bash: cd: {path}: No such file or directory\n"
        except NotADirectoryError: return f"bash: cd: {path}: Not a directory\n"
    if command == "pwd": return f"{os.getcwd()}\n"
    if command.startswith("echo"): return command.split(None,1)[1] + "\n" if len(command.split(None,1))>1 else "\n"
    if command == "exit": return "logout\n"
    if command == "whoami": return "root\n"
    return None

def fake_block_response(command: str): return "bash: permission denied\n"

def extract_command_from_amun_log(log_line: str):
    m = re.search(r'\]#\s+(.*)', log_line)
    return m.group(1).strip() if m else None

# --- Flask ---
app = Flask(__name__)

@app.route('/execute', methods=['GET'])
def execute_command_get():
    command = request.args.get('command', '')
    session = request.args.get('session', 'unknown-session')
    extracted_cmd = extract_command_from_amun_log(command)
    if extracted_cmd: command = extracted_cmd

    subs = split_commands(command)
    active = subs[-1] if subs else command
    macro, micro = parse_command(active)

    sp = session_paths.setdefault(session, [])
    sp.append((macro, micro))

    # --- HPA 阻断判断 ---
    decision, debug = should_block(hpa, session, sp)
    print("HPA debug:", json.dumps(debug, ensure_ascii=False))

    if decision:
        return fake_block_response(command)

    local = run_command_local(command)
    if local is not None:
        return local

    llm_out = get_response_from_llm(command)
    if llm_out is None:
        return f"bash: {command.split()[0]}: command not found\n"
    return llm_out + "\n"

if __name__ == '__main__':
    port = int(os.environ.get('LLM_SHELL_PORT', '12345'))
    print(f"Starting llm_shell_amun on 0.0.0.0:{port}")
    app.run(host='127.0.0.1', port=port)
