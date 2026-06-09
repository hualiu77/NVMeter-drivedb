#!/usr/bin/env python3
"""
Import USB-bridge entries from smartmontools' drivedb.h into our YAML format.

Run:
    python3 scripts/import-smartmontools.py \
        --source /opt/homebrew/Cellar/smartmontools/<ver>/share/smartmontools/drivedb.h \
        --out bridges/imported/

The script extracts the 'USB: ...' struct entries (C source format),
groups them by (chip name, smartctl_args), expands simple character-class
regexes in the product ID (e.g. 0x610[34] → 0x6103, 0x6104), and writes
one YAML file per group with all matching usb_ids: listed together.

Legal note
----------
USB IDs and smartctl command-line flags are *facts* — not copyrightable
expression. We extract them, re-arrange into our own YAML schema, and
release the output under CC0-1.0 (the rest of this repository's licence).
smartmontools is GPL-2.0-licensed source code; we explicitly do NOT
copy any code, only the underlying facts. The `imported_from` comment
in each generated file credits the source.

Imported entries carry `verified_by: []` — they ARE NOT yet verified on
macOS. Real-user PRs upgrading them to `verified_by: ["@handle"]` are
welcome.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Parse drivedb.h ─────────────────────────────────────────────────────────

# A drivedb.h USB entry looks like (lines may carry C++ trailing comments):
#
#   { "USB: <description>; <chip>",
#     "0xVID:0xPID",
#     "", // optional comment
#     "",
#     "-d sat"
#   },
#
# We match the whole struct, then peel out the five string slots.

USB_BLOCK_RE = re.compile(
    r'\{\s*'
    r'"USB:\s*([^"]*?)"\s*,\s*'        # 1: USB description string
    r'"([^"]+)"\s*,\s*'                # 2: vid:pid
    r'(?://[^\n]*\n\s*)?'              # optional trailing comment
    r'"([^"]*)"\s*,\s*'                # 3: version (often empty)
    r'(?://[^\n]*\n\s*)?'
    r'"([^"]*)"\s*,\s*'                # 4: model (often empty)
    r'(?://[^\n]*\n\s*)?'
    r'"([^"]*)"\s*'                    # 5: smartctl options
    r'(?://[^\n]*)?'                   # trailing comment on the options line
    r'\s*\}',
    re.DOTALL,
)

CHARCLASS_RE = re.compile(r'\[([0-9a-fA-F])([0-9a-fA-F])\]')           # [34]
CHARRANGE_RE = re.compile(r'\[([0-9a-fA-F])-([0-9a-fA-F])\]')          # [5-7]
ALTGROUP_RE  = re.compile(r'\(([0-9a-fA-F|\[\]\-]+)\)')                # (157|181|1ce)


def expand_pattern(pattern: str) -> list[str]:
    """Expand simple regex patterns into a list of literal hex strings.

    Handles `[ab]` character classes, `[a-c]` ranges, and `(a|b|c)`
    alternation groups. Re-runs all three until fixed-point in case an
    expansion produces fresh patterns (e.g. `(157|1[df]9)` → `(157|1d9|1f9)`).
    Anything else (`.`, `*`, `?`, backslashes) causes the entry to be
    dropped — we need exact 4-hex-digit ids.
    """
    out = [pattern]
    safety = 32  # cap so we never loop forever on weird input

    while safety > 0:
        safety -= 1
        progress = False
        new = []
        for p in out:
            # Try alternation first (highest semantic level).
            m = ALTGROUP_RE.search(p)
            if m:
                for alt in m.group(1).split("|"):
                    new.append(p[: m.start()] + alt + p[m.end():])
                progress = True
                continue
            # Then ranges.
            m = CHARRANGE_RE.search(p)
            if m:
                lo, hi = int(m.group(1), 16), int(m.group(2), 16)
                for c in range(lo, hi + 1):
                    new.append(p[: m.start()] + format(c, "x") + p[m.end():])
                progress = True
                continue
            # Then character classes.
            m = CHARCLASS_RE.search(p)
            if m:
                a, b = m.group(1), m.group(2)
                new.append(p[: m.start()] + a + p[m.end():])
                new.append(p[: m.start()] + b + p[m.end():])
                progress = True
                continue
            new.append(p)
        out = new
        if not progress:
            break

    # If anything regex-y remains, abort.
    for p in out:
        if re.search(r"[\[\]\.\*\+\?\(\)\\|]", p):
            return []
    return out


def parse_vid_pid(s: str) -> list[str]:
    """Parse `0x0080:0xa001` (or with regex on PID) → list of `xxxx:yyyy`."""
    m = re.match(r"^0x([0-9a-fA-F]{4}):0x([0-9a-fA-F\[\]\-]+)$", s.strip())
    if not m:
        return []
    vid = m.group(1).lower()
    pid_raw = m.group(2).lower()
    pids = expand_pattern(pid_raw)
    out = []
    for pid in pids:
        if len(pid) == 4 and re.match(r"^[0-9a-f]{4}$", pid):
            out.append(f"{vid}:{pid}")
    return out


def clean_args(raw: str) -> list[str]:
    """`-d sat,12` → ["-d", "sat,12"]."""
    s = raw.strip()
    if not s:
        return []
    # Defensive: drop accidental trailing C++ comment fragments.
    s = re.sub(r"\s*//.*$", "", s)
    return s.split()


def chip_label(description: str) -> str:
    """Extract a readable chip/bridge name from the 'USB: foo; bar' string."""
    if ";" in description:
        chip = description.split(";", 1)[1].strip()
    else:
        chip = description.strip()
    return chip or "Unknown bridge"


def parse_drivedb(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in USB_BLOCK_RE.finditer(text):
        desc, vidpid, _ver, _model, opts = m.groups()
        ids = parse_vid_pid(vidpid)
        args = clean_args(opts)
        # Keep no-args entries — they document "chip recognized but no
        # working SMART pass-through" which IS useful metadata. Schema
        # allows smartctl_args: []. We still need at least one usb_id.
        if not ids:
            continue
        yield {
            "chip": chip_label(desc),
            "description": desc.strip(),
            "smartctl_args": args,
            "usb_ids": ids,
        }


# ── Group & emit YAML ───────────────────────────────────────────────────────

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "entry"


def yaml_quote_args(args: list[str]) -> str:
    return "[" + ", ".join(f'"{a}"' for a in args) + "]"


def emit_yaml(group_key, entries, out_dir: Path, source_version: str):
    chip, args_tuple = group_key
    args = list(args_tuple)
    all_ids = sorted({uid for e in entries for uid in e["usb_ids"]})
    # Pick the most informative description we've seen for this chip.
    full_desc = max((e["description"] for e in entries), key=len)

    # Build a deterministic filename from chip + (a short hash of) args
    # so that two distinct (chip, args) groups never collide. We DO want
    # "ASMedia + -d sat" and "ASMedia + -d sntasmedia" to land in two
    # files, since they're different runtime behaviours.
    slug = slugify(chip)
    if args:
        args_slug = slugify("-".join(args))
        fn = out_dir / f"{slug}__{args_slug}.yaml"
    else:
        fn = out_dir / f"{slug}__noargs.yaml"

    yaml = []
    yaml.append(f'bridge: "{chip}"')
    yaml.append(f'usb_ids:')
    for uid in all_ids:
        yaml.append(f'  - "{uid}"')
    yaml.append(f'smartctl_args: {yaml_quote_args(args)}')
    yaml.append("verified_by: []")
    yaml.append("notes: |")
    yaml.append(f"  Imported from smartmontools drivedb.h ({source_version}).")
    yaml.append(f"  Original description: {full_desc}")
    yaml.append(f"")
    yaml.append(f"  Status on macOS: UNVERIFIED. The smartctl flags above work on")
    yaml.append(f"  Linux but most USB-SATA bridges are blocked by macOS's user-")
    yaml.append(f"  space SCSI stack regardless of the -d argument (see README).")
    yaml.append(f"  Please open a PR upgrading verified_by once tested.")
    fn.write_text("\n".join(yaml) + "\n", encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path,
                    help="Path to smartmontools drivedb.h")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output directory (typically bridges/imported/)")
    args = ap.parse_args()

    if not args.source.is_file():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    # Detect the drivedb version from its $Id$ header.
    head = args.source.read_text(errors="replace")[:8000]
    m = re.search(r"\$Id:\s*drivedb\.h\s+(\d+)\s+([\d\-]+)", head)
    source_version = m.group(0) if m else "unknown revision"

    # First pass: enumerate every entry in source order. Some drivedb.h
    # USB IDs appear in multiple entries (e.g. Cypress CY7C68300 family,
    # where a later, more-specific entry overrides an earlier generic
    # one). smartmontools applies "last match wins"; we follow suit by
    # de-duping USB IDs against the LATEST entry that owns them.
    all_entries = list(parse_drivedb(args.source))
    last_owner: dict[str, int] = {}
    for idx, entry in enumerate(all_entries):
        for uid in entry["usb_ids"]:
            last_owner[uid] = idx

    groups: dict = defaultdict(list)
    for idx, entry in enumerate(all_entries):
        # Trim usb_ids that a later entry has taken over.
        kept_ids = [uid for uid in entry["usb_ids"] if last_owner[uid] == idx]
        if not kept_ids:
            continue
        key = (entry["chip"], tuple(entry["smartctl_args"]))
        groups[key].append({**entry, "usb_ids": kept_ids})

    print(f"Parsed {len(all_entries)} entries; after dedup → "
          f"{sum(len(v) for v in groups.values())} kept across "
          f"{len(groups)} unique (chip, args) groups")

    written = 0
    for key, entries in sorted(groups.items()):
        emit_yaml(key, entries, args.out, source_version)
        written += 1

    print(f"Wrote {written} YAML files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
