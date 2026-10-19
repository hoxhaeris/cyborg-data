#!/usr/bin/env python3
"""Prepare index.schema.json for Go codegen.

The canonical schema (pydantic serialization mode) expresses an optional/nullable
field as ``anyOf: [T, {"type": "null"}]``. go-jsonschema maps that idiom to
``interface{}`` and duplicated inline structs, so we collapse each such ``anyOf``
to its single non-null branch ``T``. This is semantically safe for the Go
consumer: encoding/json unmarshals a JSON ``null`` into the zero value / nil
regardless.

For a collapsed *primitive* (string/number/bool) we also give the field a zero
default. go-jsonschema emits a plain value type for a field that has a default and
a pointer for one that does not, so this keeps scalars as values (``string``, not
``*string``) -- matching the historical hand-written Go structs and avoiding
pointer churn across callers. Object/array fields keep no default and so become
pointers/slices, which is correct for a field that can be absent.

Usage: prepare_codegen_schema.py <input.schema.json> <output.json>
"""

import json
import sys

_ZERO = {"string": "", "integer": 0, "number": 0, "boolean": False}


def collapse_nullable(node: object) -> None:
    """Recursively rewrite ``anyOf: [T, null]`` nodes to ``T`` in place."""
    if isinstance(node, dict):
        any_of = node.get("anyOf")
        if isinstance(any_of, list):
            non_null = [b for b in any_of if not (isinstance(b, dict) and b.get("type") == "null")]
            if len(non_null) == 1 and len(non_null) != len(any_of):
                branch = non_null[0]
                del node["anyOf"]
                node.pop("default", None)
                for key, value in branch.items():
                    node.setdefault(key, value)
                if branch.get("type") in _ZERO:
                    node["default"] = _ZERO[branch["type"]]
        for value in node.values():
            collapse_nullable(value)
    elif isinstance(node, list):
        for item in node:
            collapse_nullable(item)


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        schema = json.load(f)
    collapse_nullable(schema)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


if __name__ == "__main__":
    main()
