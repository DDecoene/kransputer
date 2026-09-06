#!/usr/bin/env python3
"""Add silkscreen pin labels to a kransputer bus-module board.

For both edge headers (J1, J2) it writes, next to every pin, on F.Silkscreen:

  pin 1  -> VDD        pin 2  -> GND
  pins 3-14 -> <group><sig>, group 1..4, sig A/B/Y   (1A 1B 1Y 2A ... 4Y)
  pins 15-16 -> BX BY  (spare BUS_X / BUS_Y lines)

Labels sit just inside the board between the header and the first gate row, so
they stay within the outline. Existing labels of this exact form are removed
first, so the script is safe to run twice.

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      label_headers.py <board.kicad_pcb> [--in-place]

Default: writes <board>.labelled.kicad_pcb and leaves the original alone.
--in-place edits the file after making a .bak. Board must be closed in KiCad.
"""
import os
import re
import shutil
import sys

import pcbnew

LABEL_Y_INSET = 3.1        # mm from the pin row toward the board centre
TEXT_MM       = 0.9
TEXT_THICK_MM = 0.14

_LABEL_RE = re.compile(r"^(VDD|GND|B[XY]|[1-4][ABY])$")


def _pin_label(k):
    if k == 1:
        return "VDD"
    if k == 2:
        return "GND"
    if k == 15:
        return "BX"
    if k == 16:
        return "BY"
    g, s = divmod(k - 3, 3)
    return f"{g + 1}{'ABY'[s]}"


def _strip_old_labels(board):
    for d in list(board.GetDrawings()):
        if (isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS
                and _LABEL_RE.match(d.GetText().strip())):
            board.Remove(d)


def _add_text(board, s, x_mm, y_mm):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(TEXT_MM), pcbnew.FromMM(TEXT_MM)))
    t.SetTextThickness(pcbnew.FromMM(TEXT_THICK_MM))
    t.SetTextAngleDegrees(90)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(t)


def label(board_path, in_place):
    lock = os.path.join(os.path.dirname(board_path),
                        "~" + os.path.basename(board_path) + ".lck")
    if os.path.exists(lock):
        sys.exit(f"board is open in KiCad ({lock} present); close it first")

    board = pcbnew.LoadBoard(board_path)

    # Read every pad coordinate into plain mm numbers first, before touching
    # the board; the SWIG footprint/pad proxies get flaky once it is mutated.
    hdr_pads = []
    for ref in ("J1", "J2"):
        hdr = board.FindFootprintByReference(ref)
        if hdr is None:
            sys.exit(f"no {ref} header on this board")
        pts = {}
        for p in hdr.Pads():
            pos = p.GetPosition()
            pts[p.GetNumber()] = (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
        hdr_pads.append(pts)

    _strip_old_labels(board)

    all_y = [y for pts in hdr_pads for (_, y) in pts.values()]
    cy = sum(all_y) / len(all_y)

    n = 0
    for pts in hdr_pads:
        row_y = next(iter(pts.values()))[1]
        toward = LABEL_Y_INSET if row_y < cy else -LABEL_Y_INSET
        for k in range(1, 17):
            xy = pts.get(str(k))
            if xy is None:
                continue
            _add_text(board, _pin_label(k), xy[0], row_y + toward)
            n += 1

    if in_place:
        shutil.copy2(board_path, board_path + ".bak")
        out = board_path
    else:
        out = os.path.splitext(board_path)[0] + ".labelled.kicad_pcb"
    pcbnew.SaveBoard(out, board)
    print(f"{n} pin labels written -> {out}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    in_place = "--in-place" in sys.argv[1:]
    if len(args) != 1:
        sys.exit("usage: label_headers.py <board.kicad_pcb> [--in-place]")
    if not os.path.exists(args[0]):
        sys.exit(f"not found: {args[0]}")
    label(args[0], in_place)


if __name__ == "__main__":
    main()
