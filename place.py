#!/usr/bin/env python3
"""Lay out a kransputer bus-module board in pcbnew.

The boards are highly regular (four identical cells between two bus headers),
so every footprint gets an exact, hand-computed position rather than a guessed
grid. Result: parts sit directly under their bus pins, aligned, no overlap,
short mostly-vertical ratsnest -> easy to autoroute afterwards.

Run with KiCad's bundled Python (pcbnew is not in the project venv):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      place.py [nand|indicator] [board.kicad_pcb]

With no board path it uses <target>_module/<target>_module.kicad_pcb under the
current directory.
"""
import os
import sys

import pcbnew

# ---- Geometry (mm) -------------------------------------------------------
PITCH        = 2.54                 # header pin pitch
X0           = 20.0                 # X of header pin 1
Y_TOP        = 20.0                 # Y of the top header (J1)
ROW_SPACING  = 22.86               # 0.9" -> row a to row j of one breadboard
Y_BOT        = Y_TOP + ROW_SPACING  # Y of the bottom header (J2)
GATE_PITCH   = 9.5                  # X distance between gate cells
X_CENTER     = X0 + 7.5 * PITCH     # midpoint of the 16-pin header
MARGIN_X_L   = 6.0                  # left board margin (houses C1 beside pin 1)
MARGIN_X_R   = 3.0
MARGIN_Y     = 4.0

Y_MID = (Y_TOP + Y_BOT) / 2.0


def gate_x(n):
    """Centre X of gate n (1..4), centred on the header."""
    return X_CENTER + (n - 2.5) * GATE_PITCH


def _vmm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def _put(by_ref, ref, x, y, rot=0.0):
    fp = by_ref.get(ref)
    if fp is None:
        return False
    fp.SetPosition(_vmm(x, y))
    fp.SetOrientationDegrees(rot)
    return True


# ---- Per-board layouts -------------------------------------------------------

def layout_nand(by_ref):
    """4x nand_gate: 2x2 SOT-23 per gate, pull-up top row, pull-down bottom."""
    placed = set()
    y_up = Y_TOP + 7.0
    y_dn = Y_BOT - 7.0
    dx = 2.6
    for n in range(1, 5):
        gx = gate_x(n)
        cells = {
            f"QPA_{n}": (gx - dx, y_up),
            f"QPB_{n}": (gx + dx, y_up),
            f"QNA_{n}": (gx - dx, y_dn),
            f"QNB_{n}": (gx + dx, y_dn),
        }
        for ref, (x, y) in cells.items():
            if _put(by_ref, ref, x, y):
                placed.add(ref)
    if _put(by_ref, "C1", X0 - 4.5, Y_MID, rot=90.0):
        placed.add("C1")
    return placed


def layout_indicator(by_ref):
    """4 gates: RN array on top, then LED|FET rows for A, B, Y."""
    placed = set()
    row_y = [Y_TOP + 9.0, Y_TOP + 13.5, Y_TOP + 18.0]
    dx = 2.4
    for n in range(1, 5):
        gx = gate_x(n)
        if _put(by_ref, f"RN{n}", gx, Y_TOP + 4.5):
            placed.add(f"RN{n}")
        for c, pin in enumerate(("A", "B", "Y")):
            if _put(by_ref, f"{pin}_{n}", gx - dx, row_y[c]):
                placed.add(f"{pin}_{n}")
            if _put(by_ref, f"Q{pin}_{n}", gx + dx, row_y[c]):
                placed.add(f"Q{pin}_{n}")
    if _put(by_ref, "C1", X0 - 4.5, Y_MID, rot=90.0):
        placed.add("C1")
    return placed


LAYOUTS = {"nand": layout_nand, "indicator": layout_indicator}


# ---- Edge.Cuts ------------------------------------------------------------

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


ZONE_INSET = 0.3   # mm the pour stays back from the board edge


def _add_gnd_zone(board, x0, y0, x1, y1):
    """Full B.Cu ground pour, inset from the edge, thermal relief on pads."""
    net = board.GetNetInfo().GetNetItem("GND")
    if net is None or net.GetNetCode() == 0:
        print("warning: no GND net on this board, skipping ground pour")
        return
    for z in list(board.Zones()):
        if z.GetZoneName() == "GND_B":
            board.Remove(z)

    i = ZONE_INSET
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x0 + i, y0 + i), (x1 - i, y0 + i),
                 (x1 - i, y1 - i), (x0 + i, y1 - i)):
        chain.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    chain.SetClosed(True)

    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNetCode(net.GetNetCode())
    z.SetZoneName("GND_B")
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.AddPolygon(chain)
    board.Add(z)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


# ---- Driver -------------------------------------------------------------------

def place(target, board_path):
    board = pcbnew.LoadBoard(board_path)
    fps = list(board.GetFootprints())
    if not fps:
        sys.exit("board has no footprints; import the netlist first")
    by_ref = {f.GetReference(): f for f in fps}

    # rot 90 lays the 1x16 pin row along +X: pin 1 at X0, pin 16 at X0+15*PITCH
    _put(by_ref, "J1", X0, Y_TOP, rot=90.0)
    _put(by_ref, "J2", X0, Y_BOT, rot=90.0)

    placed = {"J1", "J2"} | LAYOUTS[target](by_ref)

    leftover = [f for f in fps if f.GetReference() not in placed]
    for i, fp in enumerate(leftover):
        fp.SetPosition(_vmm(X0 + i * 4.0, Y_BOT + 12.0))
        print(f"warning: unplaced footprint {fp.GetReference()} parked below")

    # Outline hugs the header pin span (that is the breadboard plug width);
    # the layout keeps every part inside it by construction.
    x0 = X0 - MARGIN_X_L
    x1 = X0 + 15 * PITCH + MARGIN_X_R
    y0 = Y_TOP - MARGIN_Y
    y1 = Y_BOT + MARGIN_Y
    _draw_edge_rect(board, x0, y0, x1, y1)
    _add_gnd_zone(board, x0, y0, x1, y1)

    pcbnew.SaveBoard(board_path, board)
    print(f"placed {len(fps)} footprints, outline "
          f"{x1 - x0:.1f} x {y1 - y0:.1f} mm, B.Cu ground pour, "
          f"saved {board_path}")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "nand"
    if target not in LAYOUTS:
        sys.exit(f"unknown target {target!r}; choose from {sorted(LAYOUTS)}")
    if len(sys.argv) > 2:
        board_path = sys.argv[2]
    else:
        board_path = os.path.join(os.getcwd(), f"{target}_module",
                                  f"{target}_module.kicad_pcb")
    if not os.path.exists(board_path):
        sys.exit(f"board not found: {board_path}\n"
                 f"In KiCad: new PCB project '{target}_module', import "
                 f"{target}_module.net, save. Then rerun from that folder's "
                 f"parent, or pass the .kicad_pcb path as the 2nd argument.")
    place(target, board_path)


if __name__ == "__main__":
    main()
