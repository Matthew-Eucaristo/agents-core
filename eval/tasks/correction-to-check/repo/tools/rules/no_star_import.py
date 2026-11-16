import ast


def check(path, source):
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            problems.append((node.lineno, f"wildcard import from {node.module}"))
    return problems
