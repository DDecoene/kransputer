#!/usr/bin/env python3
"""Auto-place a kransputer bus-module board in pcbnew.

Positions the two edge headers on opposite rows, clusters each subcircuit's
footprints in the band between them, drops leftovers (C1) below, and draws a
tight Edge.Cuts rectangle.

Run with KiCad's bundled Python (pcbnew is not in the project venv):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 place.py [target]

Expects <target>_module/<target>_module.kicad_pcb next to this script, already
populated from <target>_module.net.
"""
import os
import sys

import pcbnew

import placement as pl

ROW_SPACING_MM    = 22.86     # 0.9" -> row a to row j of one breadboard
HEADER_PITCH_MM   = 2.54
ORIGIN_MM         = (40.0, 40.0)
CLUSTER_COLS      = 3
CLUSTER_PITCH_MM  = (6.0, 6.0)
GROUP_GAP_MM      = 4.0
OUTLINE_MARGIN_MM = 4.0

SHEET_ORDER = [
    "nand_gate1", "nand_gate2", "nand_gate3", "nand_gate4",
    "indicator_gate1", "indicator_gate2", "indicator_gate3", "indicator_gate4",
]


def _vmm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def _draw_edge_rect(board, x0, y0, x1, y1):
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(_vmm(ax, ay))
        seg.SetEnd(_vmm(bx, by))
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)


def place(board_path):
    board = pcbnew.LoadBoard(board_path)
    fps = list(board.GetFootprints())
    if not fps:
        sys.exit("board has no footprints; import the netlist first")
    by_ref = {f.GetReference(): f for f in fps}

    ox, oy = ORIGIN_MM
    y_top, y_bot = pl.bus_row_ys(ROW_SPACING_MM, oy)
    xs = pl.header_pin_xs(16, HEADER_PITCH_MM, ox)

    for ref, y, rot in (("J1", y_top, 0.0), ("J2", y_bot, 180.0)):
        fp = by_ref.get(ref)
        if fp is not None:
            fp.SetPosition(_vmm(xs[0], y))
            fp.SetOrientationDegrees(rot)

    placed = {"J1", "J2"}
    groups = pl.group_by_sheet(
        [(f.GetReference(), f.GetSheetname() or "") for f in fps]
    )
    ordered = [s for s in SHEET_ORDER if s in groups]
    ordered += sorted(s for s in groups
                      if s not in SHEET_ORDER and s != "root")

    band_x, band_y = ox, y_top + HEADER_PITCH_MM + GROUP_GAP_MM
    row_h = 3 * CLUSTER_PITCH_MM[1] + GROUP_GAP_MM
    for sheet in ordered:
        refs = sorted(groups[sheet], key=pl.natural_key)
        pts = pl.grid_positions(len(refs), CLUSTER_COLS,
                                CLUSTER_PITCH_MM[0], CLUSTER_PITCH_MM[1],
                                (band_x, band_y))
        for ref, (x, y) in zip(refs, pts):
            by_ref[ref].SetPosition(_vmm(x, y))
            by_ref[ref].SetOrientationDegrees(0.0)
            placed.add(ref)
        band_x += CLUSTER_COLS * CLUSTER_PITCH_MM[0] + GROUP_GAP_MM
        if band_x > xs[-1]:
            band_x, band_y = ox, band_y + row_h

    leftover = [f for f in fps if f.GetReference() not in placed]
    pts = pl.grid_positions(len(leftover), 4, 5.0, 5.0,
                            (ox, y_bot - HEADER_PITCH_MM - GROUP_GAP_MM - 10))
    for fp, (x, y) in zip(leftover, pts):
        fp.SetPosition(_vmm(x, y))

    coords = [(pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y))
              for f in fps]
    x0, y0, x1, y1 = pl.outline_rect(coords, OUTLINE_MARGIN_MM)
    _draw_edge_rect(board, x0, y0, x1, y1)

    pcbnew.SaveBoard(board_path, board)
    print(f"placed {len(fps)} footprints, drew outline, saved {board_path}")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "nand"
    if len(sys.argv) > 2:
        board_path = sys.argv[2]
    else:
        board_path = os.path.join(os.getcwd(), f"{target}_module",
                                  f"{target}_module.kicad_pcb")
    if not os.path.exists(board_path):
        sys.exit(f"board not found: {board_path}\n"
                 f"In KiCad: new PCB project '{target}_module', import "
                 f"{target}_module.net, save. Then rerun (from that folder's "
                 f"parent), or pass the .kicad_pcb path as the 2nd argument.")
    place(board_path)


if __name__ == "__main__":
    main()
