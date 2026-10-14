import re
_E = {'\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
_U = {'\\': '\\', 'n': '\n', 'r': '\r', 't': '\t'}

def esc(s):
    return ''.join(_E.get(c, c) for c in s)

def unesc(s):
    return re.sub(r'\\(.)', lambda m: _U[m.group(1)], s)
