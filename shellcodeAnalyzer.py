# shellcodeAnalyzer.py (修改版)
import os
from openai import OpenAI
from flask import Flask, request, jsonify

API_BASE = os.environ.get("SHELLCODE_API_BASE", "https://api.chatanywhere.tech")
API_KEY = os.environ.get("SHELLCODE_API_KEY", "")
MODEL = os.environ.get("SHELLCODE_MODEL", "gpt-4o-mini")
PROMPT = (
    "You are a shellcode analyzer that extracts exactly one target IP and port used for reverse connection. "
    "Return a JSON array like [\"<ip>\", \"<port>\"] and nothing else. If none found return [\"null\",\"null\"]."
)

def get_response(message):
    client = OpenAI(api_key=API_KEY, base_url=API_BASE)
    messages = [{"role":"system","content":PROMPT}, {"role":"user","content":message}]
    try:
        resp = client.chat.completions.create(model=MODEL, messages=messages)
        content = resp.choices[0].message.content.strip()
        # try parse as JSON array
        import json
        try:
            arr = json.loads(content)
            if isinstance(arr, list) and len(arr) >= 2:
                return [str(arr[0]), str(arr[1])]
        except Exception:
            # fallback: try to extract IP:port with regex
            import re
            m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})[:\s,]*(\d{1,5})', content)
            if m:
                return [m.group(1), m.group(2)]
        return ["null", "null"]
    except Exception as e:
        print("shellcode analyzer error:", e)
        return ["null", "null"]

app = Flask(__name__)

@app.route('/execute', methods=['GET'])
def execute_command_get():
    shellcode = request.args.get('shellcode', '')
    ipport = get_response(shellcode)
    return jsonify(ipport)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=int(os.environ.get("SHELLCODE_PORT", "12346")))

        

