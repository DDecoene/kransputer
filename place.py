#!/usr/bin/env python3
"""
Grove auto-plaatsing voor het logic-gates board.

Groepeert de footprints per hi[c3]rarchisch sheet (inverter1, nand_gate1, ...) zoals
SKiDL die in de netlist zet, en legt elke groep als een net rooster neer. De blokken
worden onder elkaar gestapeld. Bedoeld als startpunt: daarna schuif je met de hand bij
en route je (of exporteer je naar Freerouting).

Herbruikbaar: elke run zet absolute posities, dus je kunt 'm draaien zo vaak je wilt.

GEBRUIK
    1. Genereer de netlist:            ./venv/bin/python circuit.py
    2. In KiCad PCB editor: netlist / "Update PCB from Schematic" importeren
       EN het board opslaan (Cmd+S). Sluit daarna het board in KiCad.
    3. Draai dit script met KiCad's eigen Python (pcbnew zit niet in de venv):

       /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 place.py

    4. Heropen het board in KiCad.
"""
import os
import sys

try:
    import pcbnew
except ImportError:
    sys.exit(
        "pcbnew niet gevonden. Draai dit met KiCad's eigen Python, bv:\n"
        "  /Applications/KiCad/KiCad.app/Contents/Frameworks/"
        "Python.framework/Versions/3.9/bin/python3 place.py"
    )

# ---- Config -------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "kransputer-kicad", "kransputer-kicad.kicad_pcb")

ORIGIN_MM = (30.0, 30.0)   # linkerbovenhoek van het eerste blok
COLS = 4                   # footprints per rij binnen een groep
X_PITCH_MM = 12.0          # horizontale afstand tussen footprints
Y_PITCH_MM = 12.0          # verticale afstand tussen rijen
GROUP_GAP_MM = 10.0        # extra ruimte tussen twee groepen

# Volgorde van de groepen (van boven naar onder). Sheets die hier niet in
# staan komen er alfabetisch achteraan.
GROUP_ORDER = [
    "root",          # losse connectors (J1..J4)
    "inverter1",
    "led_indicator1",
    "nand_gate1",
    "led_indicator2",
    "nor_gate1",
    "led_indicator3",
]
# ----------------------------------------------------------------------------


def sheet_key(fp):
    """Genormaliseerde sheetnaam voor een footprint."""
    name = (fp.GetSheetname() or "").strip().strip("/")
    return name or "root"


def natural_ref(fp):
    """Sorteert Q2 voor Q10."""
    ref = fp.GetReference()
    head = ref.rstrip("0123456789")
    tail = ref[len(head):]
    return (head, int(tail) if tail else 0)


def main():
    if not os.path.exists(BOARD):
        sys.exit(f"Board niet gevonden: {BOARD}")

    board = pcbnew.LoadBoard(BOARD)
    footprints = list(board.GetFootprints())
    if not footprints:
        sys.exit(
            "Board bevat 0 footprints. Importeer eerst de netlist in KiCad "
            "en sla het board op."
        )

    # groeperen per sheet
    groups = {}
    for fp in footprints:
        groups.setdefault(sheet_key(fp), []).append(fp)

    ordered = [g for g in GROUP_ORDER if g in groups]
    ordered += sorted(g for g in groups if g not in GROUP_ORDER)

    ox, oy = ORIGIN_MM
    cursor_y = oy
    total = 0

    for group in ordered:
        members = sorted(groups[group], key=natural_ref)
        for i, fp in enumerate(members):
            row, col = divmod(i, COLS)
            x = ox + col * X_PITCH_MM
            y = cursor_y + row * Y_PITCH_MM
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            fp.SetOrientationDegrees(0)
            total += 1

        rows = (len(members) + COLS - 1) // COLS
        print(f"  {group:<16} {len(members):>2} footprints -> {rows} rij(en)")
        cursor_y += rows * Y_PITCH_MM + GROUP_GAP_MM

    pcbnew.SaveBoard(BOARD, board)
    print(f"\n{total} footprints geplaatst. Board opgeslagen: {BOARD}")


if __name__ == "__main__":
    main()
