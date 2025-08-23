import json
import os
import socket
import sys
import requests  # type: ignore
from openai import OpenAI  # type: ignore
from flask import Flask, request  # type: ignore
from hpa_manager import HPA
from blocker import should_block
import uuid

API_KEY = "sk-i2GQTkZ4h1XuFaYtPmMEAziCNZNY0zfcNCTQwwhDVy7lSJdp"
BASE_URL = "https://api.chatanywhere.tech"
MODEL = "gpt-4o-mini"

hpa = HPA()

session_map = {}  # session_id

def get_response(message):
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a shell with system information Linux svr04 3.2.0-4-amd64 #1 SMP Debian 3.2.68-1+deb7u1 x86_64 GNU/Linux with distribution Debian GNU/Linux 8.11 (jessie), now that you need to simulate a bash shell, your output should look as if you executed this command, and you should not output any other text that is not part of the response of this command"
            ),
        },
        {
            "role": "user",
            "content": message,
        },
    ]
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(e)
        return 0

def run_command(command):
    if command == "uname -a":
        return "Linux svr04 3.2.0-4-amd64 #1 SMP Debian 3.2.68-1+deb7u1 x86_64 GNU/Linux\n"
    elif command == "lsb_release -a":
        return ("No LSB modules are available.\n"
                "Distributor ID: Debian\n"
                "Description:    Debian GNU/Linux 8.11 (jessie)\n"
                "Release:        8.11\n"
                "Codename:       jessie\n")
    elif command == "dpkg --get-selections":
        return ("adduser                                    install\n"
                "apt                                        install\n"
                "base-files                                 install\n"
                "base-passwd                                install\n"
                "bash                                       install\n"
                "bsdutils                                   install\n"
                "coreutils                                  install\n"
                "dash                                       install\n"
                "debconf                                    install\n"
                "debian-archive-keyring                     install\n"
                "dpkg                                       install\n"
                "e2fslibs                                   install\n"
                "e2fsprogs                                  install\n"
                "findutils                                  install\n"
                "gcc-4.9-base                               install\n"
                "gzip                                       install\n"
                "hostname                                   install\n"
                "init                                       install\n"
                "initscripts                                install\n"
                "insserv                                    install\n"
                "libc-bin                                   install\n"
                "libc6                                      install\n"
                "libncurses5                                install\n"
                "libpam-modules                             install\n"
                "libpam-runtime                             install\n"
                "libpam0g                                   install\n"
                "login                                      install\n"
                "lsb-base                                   install\n"
                "makedev                                    install\n"
                "mawk                                       install\n"
                "mount                                      install\n"
                "ncurses-base                               install\n"
                "ncurses-bin                                install\n"
                "perl-base                                  install\n"
                "sed                                        install\n"
                "sensible-utils                             install\n"
                "sysv-rc                                    install\n"
                "sysvinit                                   install\n"
                "sysvinit-utils                             install\n"
                "tar                                        install\n"
                "util-linux                                 install\n"
                "zlib1g                                     install\n")
    elif command == "service --status-all":
        return ("[ + ]  acpid\n"
                "[ + ]  cron\n"
                "[ + ]  dbus\n"
                "[ + ]  exim4\n"
                "[ + ]  kmod\n"
                "[ + ]  networking\n"
                "[ + ]  rsyslog\n"
                "[ + ]  ssh\n"
                "[ + ]  udev\n"
                "[ - ]  procps\n")
    elif command.startswith("cat"):
        filename = command.split(" ")[1]
        try:
            with open(filename, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"cat: {filename}: No such file or directory\n"
    elif command.startswith("ls"):
        command+=" "
        path = command.split(" ")[1]
        if path == "":
            path = "."
        try:
            return " ".join(os.listdir(path)) + "\n"
        except FileNotFoundError:
            return f"ls: cannot access {path}: No such file or directory\n"
    elif command.startswith("cd"):
        path = command.split(" ")[1]
        try:
            os.chdir(path)
            return ""
        except FileNotFoundError:
            return f"bash: cd: {path}: No such file or directory\n"
    elif command == "pwd":
        return f"{os.getcwd()}\n"
    elif command.startswith("echo"):
        return command.split(" ", 1)[1] + "\n"
    elif command == "exit":
        exit()
    elif command == "whoami":
        return "root\n"
    else:
        llm_response = get_response(command)
        if llm_response==0:
            command = command.split(" ")[0]
            return f"bash: {command}: command not found\n"
        return llm_response+'\n'

def create_files():
    os.makedirs(os.path.join('.', 'etc'), exist_ok=True)
    os.makedirs(os.path.join('.', 'var', 'log'), exist_ok=True)

    with open(os.path.join('.', 'etc', 'issue'), 'w') as f:
        f.write(f"Debian GNU/Linux 8 {os.path.sep}n {os.path.sep}l\n")

    with open(os.path.join('.', 'etc', 'motd'), 'w') as f:
        f.write("The programs included with the Debian GNU/Linux system are free software;\n"
                "the exact distribution terms for each program are described in the\n"
                "individual files in /usr/share/doc/*/copyright.\n"
                "\n"
                "Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent\n"
                "permitted by applicable law.\n")

    with open(os.path.join('.', 'etc', 'passwd'), 'w') as f:
        f.write("root:x:0:0:root:/root:/bin/bash\n"
                "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
                "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
                "sync:x:4:65534:sync:/bin:/bin/sync\n"
                "games:x:5:60:games:/usr/games:/usr/sbin/nologin\n"
                "man:x:6:12:man:/var/cache/man:/usr/sbin/nologin\n"
                "lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin\n"
                "mail:x:8:8:mail:/var/mail:/usr/sbin/nologin\n"
                "news:x:9:9:news:/var/spool/news:/usr/sbin/nologin\n"
                "uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin\n"
                "proxy:x:13:13:proxy:/bin:/usr/sbin/nologin\n"
                "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
                "backup:x:34:34:backup:/var/backups:/usr/sbin/nologin\n"
                "list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin\n"
                "irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin\n"
                "gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin\n"
                "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n")

    with open(os.path.join('.', 'etc', 'shadow'), 'w') as f:
        f.write("root:*:17837:0:99999:7:::\n"
                "daemon:*:17837:0:99999:7:::\n"
                "bin:*:17837:0:99999:7:::\n"
                "sys:*:17837:0:99999:7:::\n"
                "sync:*:17837:0:99999:7:::\n"
                "games:*:17837:0:99999:7:::\n"
                "man:*:17837:0:99999:7:::\n"
                "lp:*:17837:0:99999:7:::\n"
                "mail:*:17837:0:99999:7:::\n"
                "news:*:17837:0:99999:7:::\n"
                "uucp:*:17837:0:99999:7:::\n"
                "proxy:*:17837:0:99999:7:::\n"
                "www-data:*:17837:0:99999:7:::\n"
                "backup:*:17837:0:99999:7:::\n"
                "list:*:17837:0:99999:7:::\n"
                "irc:*:17837:0:99999:7:::\n"
                "gnats:*:17837:0:99999:7:::\n"
                "nobody:*:17837:0:99999:7:::\n")

    with open(os.path.join('.', 'etc', 'network', 'interfaces'), 'w') as f:
        f.write("# This file describes the network interfaces available on your system\n"
                "# and how to activate them. For more information, see interfaces(5).\n"
                "\n"
                "# The loopback network interface\n"
                "auto lo\n"
                "iface lo inet loopback\n"
                "\n"
                "# The primary network interface\n"
                "allow-hotplug eth0\n"
                "iface eth0 inet dhcp\n")

    with open(os.path.join('.', 'etc', 'resolv.conf'), 'w') as f:
        f.write("nameserver 8.8.8.8\n"
                "nameserver 8.8.4.4\n")


def split_commands(cmd: str):
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
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == '{' and not in_single_quote and not in_double_quote:
            brace_level += 1
        elif char == '}' and not in_single_quote and not in_double_quote:
            brace_level = max(0, brace_level - 1)

        # splite or not
        if not in_single_quote and not in_double_quote and brace_level == 0:
            # `&&`
            if cmd[i:i+2] == '&&':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            #  `||`
            elif cmd[i:i+2] == '||':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            #  `;` or `|`
            elif char in [';', '|']:
                result.append(current.strip())
                current = ''
                i += 1
                continue

        # Accumulative char
        current += char
        i += 1

    if current.strip():
        result.append(current.strip())

    return result


# extract macro & micro state
def parse_command(cmd: str):
    """
    input: sub command (string)
    output: List of (macro, micro) pairs
    """
    # remove parentheses
    cmd = cmd.replace('(', '').replace(')', '')

    commands = split_commands(cmd)
    result = []

    for sub_cmd in commands:
        sub_cmd = sub_cmd.strip()
        if not sub_cmd:
            continue

        parts = sub_cmd.split(None, 1)  # split on any whitespace, at most 1 split
        macro = parts[0]
        micro = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "none"

        result.append((macro, micro))

    return result


def execute_with_hpa(session_id, commands):
    from hpa_manager import HPA
    from blocker import should_block

    hpa = HPA()
    output = ""

    for position, command in enumerate(commands):
        parsed_cmds = parse_command(command)  # [(macro, micro), ...]
        
        for macro, micro in parsed_cmds:
            matched = hpa.match_hpa(position, macro, micro)
            hpa.update_src_and_dst(session_id, src=0, dst=position, blocked=False)

            if should_block(hpa, session_id, [(position, macro, micro)], src=0, dst=position, matched=matched):
                output += "bash: permission denied\n"
            else:
                if not matched:
                    hpa.update_hpa(position, macro, micro)
                output += run_command(command)

    return output

# --------------------------------------
# Flask API
# --------------------------------------
app = Flask(__name__)

@app.route('/execute', methods=['GET'])
def execute_command_get():
    command = request.args.get('command')
    dialog_id = request.args.get('dialog_id', 'default')
    output = execute_with_hpa(command, dialog_id)
    return output

# --------------------------------------
# test
# --------------------------------------
def test(command, dialog_id='default'):
    url = "http://127.0.0.1:12345/execute"
    params = {"command": command, "dialog_id": dialog_id}
    response = requests.get(url, params=params)
    print(response.text)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=12345)
