import json 
import os
import socket
import sys
import requests  # type: ignore
from openai import OpenAI  # type: ignore
from flask import Flask, request  # type: ignore

from session import Session
from command_parser import parse_command
  

API_KEY = "sk-i2GQTkZ4h1XuFaYtPmMEAziCNZNY0zfcNCTQwwhDVy7lSJdp"
BASE_URL = "https://api.chatanywhere.tech"
MODEL = "gpt-4o-mini"


sessions = {}

def new_session(session_id):
    session = Session(session_id)
    sessions[session_id] = session
    return session

def process_command(session_id, command):
    if session_id not in sessions:
        session = new_session(session_id)
    else:
        session = sessions[session_id]
    session.add_command(command)
    return session.should_block()

def handle_command(session_id, command):
    # HPA / session
    should_block_flag = process_command(session_id, command)
    
    session = sessions[session_id]

    current_position = getattr(session, "current_node_id", None)
    payoff = session.get_payoff()
    matched = session.matched
    process_vector = session.process_vector
    
    # console for debug
    print(
        f"[DEBUG] Command: {command}\n"
        f"[DEBUG] matched: {matched}\n"
        f"[DEBUG] payoff: {payoff}\n"
        f"[DEBUG] should_block: {should_block_flag}\n"
        f"[DEBUG] current_position: {current_position}\n"
        f"[DEBUG] process_vector: {process_vector}\n"
    )
    
    # blcok response
    if should_block_flag:
        return "permission denied\n"
    else:
        return run_command(command)


def get_response(message):
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a shell with system information Linux svr04 3.2.0-4-amd64 "
                "#1 SMP Debian 3.2.68-1+deb7u1 x86_64 GNU/Linux with distribution "
                "Debian GNU/Linux 8.11 (jessie), now that you need to simulate a bash shell, "
                "your output should look as if you executed this command, and you should not "
                "output any other text that is not part of the response of this command"
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
    elif command == "whoami":
        return "root\n"
    elif command.startswith("cat"):
        filename = command.split(" ")[1]
        try:
            with open(filename, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"cat: {filename}: No such file or directory\n"
    elif command.startswith("ls"):
        command += " "
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
    else:
        llm_response = get_response(command)
        if llm_response == 0:
            command = command.split(" ")[0]
            return f"bash: {command}: command not found\n"
        return llm_response + '\n'



# -------- Flask API --------
app = Flask(__name__)

@app.route('/execute', methods=['GET'])
def execute_command_get():
    session_id = request.args.get('session', 'default')
    command = request.args.get('command')
    output = handle_command(session_id, command)
    return output


def test(command, session_id='default'):
    url = "http://127.0.0.1:12345/execute"
    params = {"command": command, "session": session_id}
    response = requests.get(url, params=params)
    print(response.text)
