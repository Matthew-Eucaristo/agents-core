import importlib.util
import pathlib
import sys

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
RULES_DIR = TOOLS_DIR / "rules"


def load_rules():
    rules = []
    for rule_file in sorted(RULES_DIR.glob("*.py")):
        if rule_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"lint_rule_{rule_file.stem}", rule_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rules.append((rule_file.stem, module.check))
    return rules


def source_files(root):
    for file in sorted(root.rglob("*.py")):
        relative = file.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        yield relative.as_posix(), file.read_text()


def check_source(path, source, rules=None):
    problems = []
    for name, check in rules if rules is not None else load_rules():
        for line, message in check(path, source):
            problems.append(f"{path}:{line}: [{name}] {message}")
    return problems


def check_tree(root=ROOT):
    rules = load_rules()
    problems = []
    for path, source in source_files(root):
        problems.extend(check_source(path, source, rules))
    return problems


def main():
    problems = check_tree()
    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} problem(s) found")
        return 1
    print("lint ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
