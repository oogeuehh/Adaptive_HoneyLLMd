import urllib.parse

def split_commands(cmd):
    result = []
    current = ''
    i = 0
    length = len(cmd)
    in_single_quote = False
    in_double_quote = False
    brace_level = 0
    bracket_level = 0

    while i < length:
        char = cmd[i]

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        
        if not in_single_quote and not in_double_quote:
            if char == '{':
                brace_level += 1
            elif char == '}':
                brace_level = max(0, brace_level - 1)
            elif char == '(':
                bracket_level += 1
            elif char == ')':
                bracket_level = max(0, bracket_level - 1)

        if not in_single_quote and not in_double_quote and brace_level == 0 and bracket_level == 0:
            if i + 1 < length and cmd[i:i+2] == '&&':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            elif i + 1 < length and cmd[i:i+2] == '||':
                result.append(current.strip())
                current = ''
                i += 2
                continue
            elif char in [';', '|']:
                result.append(current.strip())
                current = ''
                i += 1
                continue

        current += char
        i += 1

    if current.strip():
        result.append(current.strip())

    return result


def parse_command(cmd):
    try:
        cmd = urllib.parse.unquote(cmd)
    except:
        pass
    
    cmd = cmd.strip().replace('(', ' ').replace(')', ' ')
    commands = split_commands(cmd)
    result = []

    for sub_cmd in commands:
        sub_cmd = sub_cmd.strip()
        if not sub_cmd:
            continue
        parts = sub_cmd.split(None, 1)
        macro = parts[0]
