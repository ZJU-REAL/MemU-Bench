#!/usr/bin/env python3
"""Scan fixed_tasks directory and generate tasks_map.json.

Extracts the `goal` property from each task class in user_X_Y.py files,
resolves f-string references to class attributes, and writes the result
to memory_generation/tasks_map.json.
"""

import ast
import json
import os
import re

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
FIXED_TASKS_DIR = os.path.join(
    PROJECT_ROOT, "android_world", "task_evals", "fixed_tasks"
)
OUTPUT_PATH = os.path.join(CURRENT_DIR, "tasks_map.json")


def extract_class_attributes(class_node: ast.ClassDef) -> dict[str, str]:
    """Extract class-level attribute assignments (e.g., _CONTACT_NAME = 'foo', app_name = 'foo')."""
    attrs = {}
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    val = _eval_literal(node.value)
                    if val is not None:
                        attrs[target.id] = val
    return attrs


def _eval_literal(node: ast.expr) -> str | None:
    """Try to evaluate a simple literal or .strip() call to a string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # Handle ''.strip() pattern
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "strip"
    ):
        inner = _eval_literal(node.func.value)
        if inner is not None:
            return inner.strip()
    return None


def resolve_fstring(node: ast.JoinedStr, attrs: dict[str, str]) -> str:
    """Resolve an f-string using class attributes."""
    parts = []
    for val in node.values:
        if isinstance(val, ast.Constant):
            parts.append(val.value)
        elif isinstance(val, ast.FormattedValue):
            # Handle self._XXX references
            if (
                isinstance(val.value, ast.Attribute)
                and isinstance(val.value.value, ast.Name)
                and val.value.value.id == "self"
            ):
                attr_name = val.value.attr
                if attr_name in attrs:
                    parts.append(attrs[attr_name])
                else:
                    parts.append(f"{{{attr_name}}}")
            else:
                # Fallback: try to unparse the expression
                parts.append(f"{{{ast.unparse(val.value)}}}")
    return "".join(parts)


def extract_goal_string(node: ast.expr, attrs: dict[str, str]) -> str | None:
    """Extract the goal string from a return statement, resolving f-strings."""
    # Simple string: return "..."
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    # f-string: return f"..."
    if isinstance(node, ast.JoinedStr):
        return resolve_fstring(node, attrs)

    # Parenthesized expression: return ("..." "...") or (f"..." f"...")
    if isinstance(node, ast.Tuple):
        parts = []
        for elt in node.elts:
            part = extract_goal_string(elt, attrs)
            if part is None:
                return None
            parts.append(part)
        return "".join(parts)

    # Implicit string concatenation in ast: JoinedStr with multiple parts
    # or BinOp for string concatenation
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = extract_goal_string(node.left, attrs)
        right = extract_goal_string(node.right, attrs)
        if left is not None and right is not None:
            return left + right

    return None


def extract_goals_from_file(filepath: str) -> list[str]:
    """Parse a Python file and extract all goal strings from task classes."""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    goals = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Extract class-level attributes for f-string resolution
        attrs = extract_class_attributes(node)

        # Find the goal property
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "goal":
                continue
            # Look for return statement
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    goal = extract_goal_string(stmt.value, attrs)
                    if goal is not None:
                        goals.append(goal)

    return goals


def main():
    # Scan for user_X_Y.py files
    pattern = re.compile(r"^user_(\d+)_(short|medium|long)\.py$")
    tasks_map: dict[str, dict[str, list[str]]] = {}

    for filename in sorted(os.listdir(FIXED_TASKS_DIR)):
        m = pattern.match(filename)
        if not m:
            continue

        user_num = m.group(1)
        subdir = m.group(2)
        user_key = f"user{user_num}"

        filepath = os.path.join(FIXED_TASKS_DIR, filename)
        goals = extract_goals_from_file(filepath)

        if user_key not in tasks_map:
            tasks_map[user_key] = {}
        tasks_map[user_key][subdir] = goals

        print(f"  {filename}: {len(goals)} goals extracted")

    # Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks_map, f, ensure_ascii=False, indent=4)

    print(f"\nWrote tasks_map.json to {OUTPUT_PATH}")
    print(f"Users: {list(tasks_map.keys())}")
    for user, subdirs in tasks_map.items():
        for subdir, goals in subdirs.items():
            print(f"  {user}/{subdir}: {len(goals)} tasks")


if __name__ == "__main__":
    main()