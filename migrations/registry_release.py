"""Historical manifest ID algorithm. The independent runtime bundle check covers whole files."""

import ast
from functools import lru_cache
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "app/dynamic_plan.py": ["Task", "Proposal", "PARENTS", "compile_plan", "planner_body"],
    "app/workforce_gateway.py": ["SKILLS", "PROMPT_VERSION", "SECTIONS", "request_body", "validate_output", "quality"],
    "app/registry_qa.py": ["assess_role"],
    "app/workforce_evidence.py": ["PATTERNS", "RULESET", "normalize", "assess"],
}


@lru_cache(maxsize=1)
def adapter_digest():
    parts = []
    for filename, names in SOURCES.items():
        source = (ROOT / filename).read_text(encoding="utf-8")
        definitions = {}
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                definitions[node.name] = node
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        definitions[target.id] = node
        parts.extend(ast.get_source_segment(source, definitions[name]) for name in names)
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()
