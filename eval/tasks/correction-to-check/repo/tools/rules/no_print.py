import ast

EXEMPT_PREFIXES = ("tools/",)


def check(path, source):
    if path.startswith(EXEMPT_PREFIXES):
        return []
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            problems.append((node.lineno, "print() call; use logging instead"))
    return problems
