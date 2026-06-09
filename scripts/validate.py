#!/usr/bin/env python3
"""Validate every YAML file under bridges/ against schema/bridge.schema.json.

Usage:  python3 scripts/validate.py
Requires:  pip install pyyaml jsonschema
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "bridge.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def main() -> int:
    errors = 0
    seen_usb_ids: dict[str, str] = {}

    for path in sorted((ROOT / "bridges").rglob("*.y*ml")):
        data = yaml.safe_load(path.read_text())
        for err in VALIDATOR.iter_errors(data):
            print(f"::error file={path}::{err.message} (at {'/'.join(map(str, err.absolute_path))})")
            errors += 1

        for uid in data.get("usb_ids", []) or []:
            if uid in seen_usb_ids and seen_usb_ids[uid] != path.name:
                print(f"::error file={path}::USB ID {uid} duplicated, also in {seen_usb_ids[uid]}")
                errors += 1
            seen_usb_ids[uid] = path.name

    if errors:
        print(f"\n{errors} validation error(s).", file=sys.stderr)
        return 1
    print(f"OK — {len(list((ROOT / 'bridges').rglob('*.y*ml')))} bridge entries validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
