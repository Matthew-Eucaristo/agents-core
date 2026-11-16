import ast

CLIENT_PREFIX = "client/"
SERVER_ONLY_PACKAGE = "server_only"


def imported_modules(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module] if node.module else [alias.name for alias in node.names]
    return []


def check(path, source):
    if not path.startswith(CLIENT_PREFIX):
        return []
    problems = []
    for node in ast.walk(ast.parse(source)):
        for module in imported_modules(node):
            if module.split(".")[0] == SERVER_ONLY_PACKAGE:
                problems.append((node.lineno, f"client code must not import {module}; use shared/ instead"))
    return problems
