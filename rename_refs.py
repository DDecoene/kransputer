#!/usr/bin/env python3
"""Rename component references on a placed/routed board to the short scheme.

  NAND_<n>_QPA  -> QPA_<n>     (and QPB/QNA/QNB)
  NAND_<n>_A    -> A_<n>       (indicator LEDs; and B/Y)
  NAND_<n>_QA   -> QA_<n>      (indicator buffer FETs; and QB/QY)

Only the Reference (and, for indicator LEDs, the matching Value) field is
touched. Tracks, vias, zones, positions and net names are left exactly as they
are. Already-renamed parts are skipped, so it is safe to run twice.

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      rename_refs.py <board.kicad_pcb> [--in-place]

Default: writes <board>.renamed.kicad_pcb next to the input and leaves the
original untouched. --in-place edits the file after making a .bak copy.
The board must be closed in KiCad (no ~<name>.kicad_pcb.lck present).
"""
import os
import re
import shutil
import sys

import pcbnew

_PATTERNS = [
    (re.compile(r"^NAND_([1-4])_(QP[AB]|QN[AB])$"), lambda m: f"{m[2]}_{m[1]}"),
    (re.compile(r"^NAND_([1-4])_Q([ABY])$"),        lambda m: f"Q{m[2]}_{m[1]}"),
    (re.compile(r"^NAND_([1-4])_([ABY])$"),          lambda m: f"{m[2]}_{m[1]}"),
]


def _new_ref(old):
    for rx, sub in _PATTERNS:
        m = rx.match(old)
        if m:
            return sub(m)
    return None


def rename(board_path, in_place):
    lock = os.path.join(os.path.dirname(board_path),
                        "~" + os.path.basename(board_path) + ".lck")
    if os.path.exists(lock):
        sys.exit(f"board is open in KiCad ({lock} present); close it first")

    board = pcbnew.LoadBoard(board_path)
    changes = []
    for fp in board.GetFootprints():
        old = fp.GetReference()
        new = _new_ref(old)
        if not new or new == old:
            continue
        fp.SetReference(new)
        if fp.GetValue() == old:          # indicator LEDs carry the name as Value
            fp.SetValue(new)
        changes.append((old, new))

    if not changes:
        print("nothing to rename (already short, or not a NAND/indicator board)")
        return

    if in_place:
        shutil.copy2(board_path, board_path + ".bak")
        out = board_path
    else:
        out = os.path.splitext(board_path)[0] + ".renamed.kicad_pcb"
    pcbnew.SaveBoard(out, board)

    for old, new in sorted(changes):
        print(f"  {old:14} -> {new}")
    print(f"{len(changes)} references renamed -> {out}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    in_place = "--in-place" in sys.argv[1:]
    if len(args) != 1:
        sys.exit("usage: rename_refs.py <board.kicad_pcb> [--in-place]")
    if not os.path.exists(args[0]):
        sys.exit(f"not found: {args[0]}")
    rename(args[0], in_place)


if __name__ == "__main__":
    main()
