"""Load byte-for-byte pinned backend validators without application dependencies.

Only import wiring changes in memory: Settings is a postponed type annotation;
the shared error import points at the separately loaded, unchanged vendor file.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys
import types

VENDOR = Path(__file__).resolve().parent / "vendor"
PROVENANCE = json.loads((VENDOR / "provenance.json").read_text())


def load(name):
    path = VENDOR / f"{name}.py"
    raw = path.read_bytes()
    record = next(row for row in PROVENANCE["files"] if row["path"].endswith('/' + path.name))
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError(f"Pinned backend file changed: {path.name}")
    tree = ast.parse(raw, filename=str(path))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "src.core.config":
            if [(item.name, item.asname) for item in node.names] != [("Settings", None)]:
                raise ValueError("Unexpected backend dependency; refresh loader explicitly")
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "src.modules.content.service_kc_quiz_contract_error":
            node.module = "_vlearn_service_kc_quiz_contract_error"
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src."):
            raise ValueError(f"Unexpected backend dependency: {node.module}")
        nodes.append(node)
    tree.body = nodes
    module = types.ModuleType(f"_vlearn_{name}")
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


errors = load("service_kc_quiz_contract_error")
pair = load("service_kc_quiz_pair")
graph = load("service_kc_quiz_contract")
