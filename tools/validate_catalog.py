#!/usr/bin/env python3
"""Validate the Crowns manifest and every referenced board pack."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
PACK_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
def fail(message: str) -> None: raise ValueError(message)
def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if manifest.get("schemaVersion") != 1 or manifest.get("contentVersion", 0) < 1: fail("unsupported manifest version")
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs: fail("manifest must contain packs")
    seen, total = set(), 0
    for pack in packs:
        pack_id = pack.get("id", "")
        if not PACK_ID.fullmatch(pack_id) or pack_id in seen: fail(f"invalid or duplicate pack id: {pack_id!r}")
        seen.add(pack_id)
        relative = Path(pack.get("file", ""))
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".crowns": fail(f"unsafe pack path: {relative}")
        data = (ROOT / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != pack.get("sha256"): fail(f"hash mismatch: {pack_id}")
        boards = json.loads(data)
        if len(boards) != pack.get("boardCount"): fail(f"board count mismatch: {pack_id}")
        if not 1 <= len(boards) <= 100: fail(f"pack size must be 1...100: {pack_id}")
        for index, board in enumerate(boards):
            label, n, ids, palette = f"{pack_id} board {index + 1}", board.get("n"), board.get("ids"), board.get("palette")
            if not isinstance(board.get("name"), str) or not board["name"].strip(): fail(f"missing name: {label}")
            if not isinstance(n, int) or not 4 <= n <= 20: fail(f"invalid size: {label}")
            if not isinstance(ids, list) or len(ids) != n or any(len(row) != n for row in ids): fail(f"grid is not {n}x{n}: {label}")
            if not isinstance(palette, list) or len(palette) != n or any(not HEX.fullmatch(c) for c in palette): fail(f"invalid palette: {label}")
            if {value for row in ids for value in row} != set(range(n)): fail(f"region IDs must be exactly 0...{n - 1}: {label}")
        total += len(boards)
    print(f"Validated {len(packs)} pack(s), {total} board(s).")
    return 0
if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
