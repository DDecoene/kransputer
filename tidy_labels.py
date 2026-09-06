#!/usr/bin/env python3
"""Tidy component labels on a placed/routed kransputer board.

1. Drop the underscore from short refs:  QPA_1 -> QPA1, A_1 -> A1, QA_1 -> QA1
   (RN1 / C1 / J1 / J2 are left alone). The matching Value field on LEDs is
   updated too.
2. Move the NAND transistor reference text off the header pin labels and into
   the empty band between the pull-up and pull-down rows, at a smaller size:
     QPA<n>/QPB<n>  -> 2.6 mm below the part
     QNA<n>/QNB<n>  -> 2.6 mm above the part

Tracks, vias, zones, footprint positions and net names are not touched.
Idempotent.

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      tidy_labels.py <board.kicad_pcb> [--in-place]

Default writes <board>.tidy.kicad_pcb; --in-place edits after a .bak. Board
must be closed in the KiCad PCB editor.
"""
import os
import re
import shutil
import sys

import pcbnew

REF_TEXT_MM   = 0.8
REF_TEXT_THK  = 0.12
REF_OFFSET_MM = 2.6

_RENAME_RE = re.compile(r"^([A-Za-z]{1,3})_([1-4])$")   # QPA_1, A_1, QA_1
_PULLUP_RE = re.compile(r"^QP[AB][1-4]$")
_PULLDN_RE = re.compile(r"^QN[AB][1-4]$")


def _renamed(ref):
    m = _RENAME_RE.match(ref)
    return f"{m[1]}{m[2]}" if m else None


def tidy(board_path, in_place):
    lock = os.path.join(os.path.dirname(board_path),
                        "~" + os.path.basename(board_path) + ".lck")
    if os.path.exists(lock):
        sys.exit(f"PCB editor has this board open ({lock}); close it first")

    board = pcbnew.LoadBoard(board_path)

    renames, moves = [], 0
    for fp in board.GetFootprints():
        old = fp.GetReference()
        new = _renamed(old)
        if new and new != old:
            if fp.GetValue() == old:
                fp.SetValue(new)
            fp.SetReference(new)
            renames.append((old, new))
        ref = fp.GetReference()

        if _PULLUP_RE.match(ref) or _PULLDN_RE.match(ref):
            dy = REF_OFFSET_MM if _PULLUP_RE.match(ref) else -REF_OFFSET_MM
            t = fp.Reference()
            t.SetFPRelativePosition(pcbnew.VECTOR2I(0, pcbnew.FromMM(dy)))
            t.SetTextAngleDegrees(0)
            t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(REF_TEXT_MM),
                                         pcbnew.FromMM(REF_TEXT_MM)))
            t.SetTextThickness(pcbnew.FromMM(REF_TEXT_THK))
            moves += 1

    if in_place:
        shutil.copy2(board_path, board_path + ".bak")
        out = board_path
    else:
        out = os.path.splitext(board_path)[0] + ".tidy.kicad_pcb"
    pcbnew.SaveBoard(out, board)

    for old, new in sorted(renames):
        print(f"  {old:8} -> {new}")
    print(f"{len(renames)} refs renamed, {moves} ref texts repositioned -> {out}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    in_place = "--in-place" in sys.argv[1:]
    if len(args) != 1:
        sys.exit("usage: tidy_labels.py <board.kicad_pcb> [--in-place]")
    if not os.path.exists(args[0]):
        sys.exit(f"not found: {args[0]}")
    tidy(args[0], in_place)


if __name__ == "__main__":
    main()
