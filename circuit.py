#!/usr/bin/env python3
"""Generate KiCad netlists for the kransputer bus modules.

Each module is a breadboard-pluggable board that carries an identical 16-pin
pass-through bus on two opposite edge headers.

TARGET (or argv[1]) selects the board:
  nand       4x discrete static-CMOS 2-input NAND gate
  indicator  12-channel buffered bus LED indicator

Output: <target>_module.net
"""
import sys

import kicad_env  # noqa: F401  - points skidl at the KiCad libs; keep before skidl

from skidl import (
    Part, Net, subcircuit, generate_netlist, set_default_tool, POWER,
)

try:
    from skidl import KICAD8 as KICAD_TOOL
except ImportError:
    try:
        from skidl import KICAD7 as KICAD_TOOL
    except ImportError:
        from skidl import KICAD as KICAD_TOOL

set_default_tool(KICAD_TOOL)

# ---- Footprints ------------------------------------------------------------
FP_SOT23  = "Package_TO_SOT_SMD:SOT-23"
FP_LED    = "LED_SMD:LED_0805_2012Metric"
FP_CAP    = "Capacitor_SMD:C_0805_2012Metric"
FP_HDR16  = "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical"
FP_RARRAY = "Resistor_SMD:R_Array_Convex_4x0603"

# ---- Values ----------------------------------------------------------------
LED_R  = "1k"   # LED series resistor on the indicator board (2k2 = softer)
BULK_C = "1u"   # per-board bulk decoupling

# ---- Bus ------------------------------------------------------------------
# Pin k (1-based) carries BUS[k - 1]. Both edge headers use this map 1:1, so
# any signal is reachable from either edge.
BUS = [
    "VDD", "GND",
    "NAND_1_A", "NAND_1_B", "NAND_1_Y",
    "NAND_2_A", "NAND_2_B", "NAND_2_Y",
    "NAND_3_A", "NAND_3_B", "NAND_3_Y",
    "NAND_4_A", "NAND_4_B", "NAND_4_Y",
    "BUS_X", "BUS_Y",          # spare bus lines, edge-to-edge only
]


def add_bus_headers(nets):
    """Create edge headers J1/J2 and wire every pin to its bus net.

    `nets` maps bus-net name -> Net; names not present get a fresh Net (used
    for the spare BUS_X/BUS_Y lines on boards that do not drive them).
    Returns (j1, j2).
    """
    for name in BUS:
        nets.setdefault(name, Net(name))
    j1 = Part("Connector", "Conn_01x16_Pin", ref="J1", value="BUS_A",
              footprint=FP_HDR16)
    j2 = Part("Connector", "Conn_01x16_Pin", ref="J2", value="BUS_B",
              footprint=FP_HDR16)
    for k, name in enumerate(BUS, start=1):
        nets[name] += j1[k], j2[k]
    return j1, j2


# ---- Gate subcircuits ----------------------------------------------------


@subcircuit
def nand_gate(inst, a, b, y, vdd, gnd):
    """Discrete static-CMOS 2-input NAND.

    `inst` (e.g. "NAND_1") prefixes the four transistor refs. Pull-up is two
    BSS84 in parallel; pull-down is two BSS138 in series through an internal
    node `<inst>_MID`.
    """
    qpa = Part("Transistor_FET", "BSS84",  ref=f"{inst}_QPA", footprint=FP_SOT23)
    qpb = Part("Transistor_FET", "BSS84",  ref=f"{inst}_QPB", footprint=FP_SOT23)
    qna = Part("Transistor_FET", "BSS138", ref=f"{inst}_QNA", footprint=FP_SOT23)
    qnb = Part("Transistor_FET", "BSS138", ref=f"{inst}_QNB", footprint=FP_SOT23)
    mid = Net(f"{inst}_MID")

    a   += qpa["G"], qna["G"]
    b   += qpb["G"], qnb["G"]
    vdd += qpa["S"], qpb["S"]
    y   += qpa["D"], qpb["D"], qna["D"]
    mid += qna["S"], qnb["D"]
    gnd += qnb["S"]


# Preserved from baseline commit bf6a3a1 for the future NOR / NOT module specs.
# These still use the pre-bus-module signature (va, vb, vout, ...) and no
# semantic refs; rewrite them like nand_gate when those specs are implemented.
# Not wired by any build() below.


@subcircuit
def nor_gate(va, vb, vout, vdd, gnd):
    """Pure static-CMOS 2-input NOR gate."""
    qp1 = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    qp2 = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    qn1 = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)
    qn2 = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)
    p_internal = Net()

    va.connect(qp1['G'], qn1['G'])
    vb.connect(qp2['G'], qn2['G'])

    vdd.connect(qp1['S'])
    p_internal.connect(qp1['D'], qp2['S'])

    gnd.connect(qn1['S'], qn2['S'])
    vout.connect(qp2['D'], qn1['D'], qn2['D'])


@subcircuit
def inverter(vin, vout, vdd, gnd):
    """Pure static-CMOS inverter (NOT gate)."""
    q_p = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    q_n = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)

    vin.connect(q_p['G'], q_n['G'])
    vdd.connect(q_p['S'])
    gnd.connect(q_n['S'])
    vout.connect(q_p['D'], q_n['D'])


# ---- Board assemblies ----------------------------------------------------


def _signal_nets():
    """The 12 gate-signal nets, keyed by name."""
    sig = {}
    for n in range(1, 5):
        for p in ("A", "B", "Y"):
            name = f"NAND_{n}_{p}"
            sig[name] = Net(name)
    return sig


def _bulk_cap(vdd, gnd):
    c1 = Part("Device", "C", ref="C1", value=BULK_C, footprint=FP_CAP)
    vdd += c1[1]
    gnd += c1[2]
    return c1


def assemble_nand_module():
    """4x nand_gate + bulk cap + bus headers. Operates on the default circuit."""
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER
    gnd.drive = POWER
    sig = _signal_nets()
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for n in range(1, 5):
        nand_gate(
            f"NAND_{n}",
            sig[f"NAND_{n}_A"], sig[f"NAND_{n}_B"], sig[f"NAND_{n}_Y"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets)


def build_nand_module():
    assemble_nand_module()
    generate_netlist(file_="nand_module.net", do_backup=False)


# ---- Indicator board ----------------------------------------------------

# (LED-anode-side pin, VDD-side pin) for each Device:R_Pack04 resistor used by
# a channel; the 4th resistor (pins 4 & 5) is parked on GND. See SYMBOLS.md.
_RARRAY_PAIRS = [("1", "8"), ("2", "7"), ("3", "6")]
_RARRAY_SPARE = ("4", "5")


@subcircuit
def indicator_gate(gate, inst_no, sig_a, sig_b, sig_y, vdd, gnd):
    """Three buffered LED indicators for one gate's A/B/Y bus signals.

    Per channel a BSS138 in common source (gate = bus signal, high impedance,
    so the logic net is not loaded) sinks an LED whose anode is fed from VDD
    through one element of the `RN<inst_no>` array. LED lit = logic 1.
    """
    rn = Part("Device", "R_Pack04", ref=f"RN{inst_no}", value=LED_R,
              footprint=FP_RARRAY)
    for (led_pin, vdd_pin), pin, signal in zip(
        _RARRAY_PAIRS, ("A", "B", "Y"), (sig_a, sig_b, sig_y)
    ):
        q = Part("Transistor_FET", "BSS138", ref=f"{gate}_Q{pin}",
                 footprint=FP_SOT23)
        d = Part("Device", "LED", ref=f"{gate}_{pin}", value=f"{gate}_{pin}",
                 footprint=FP_LED)
        vdd    += rn[vdd_pin]
        gnd    += q["S"]
        signal += q["G"]
        d["K"] += q["D"]
        d["A"] += rn[led_pin]
    # park the unused 4th resistor so its pads are not left floating
    gnd += rn[_RARRAY_SPARE[0]], rn[_RARRAY_SPARE[1]]


def assemble_indicator_module():
    """12 buffered LEDs (4 gates x A/B/Y) + bulk cap + bus headers."""
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER
    gnd.drive = POWER
    sig = _signal_nets()
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for n in range(1, 5):
        indicator_gate(
            f"NAND_{n}", n,
            sig[f"NAND_{n}_A"], sig[f"NAND_{n}_B"], sig[f"NAND_{n}_Y"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets)


def build_indicator_module():
    assemble_indicator_module()
    generate_netlist(file_="indicator_module.net", do_backup=False)


# ---- Entry point ------------------------------------------------------------

TARGET = "nand"

BUILDERS = {
    "nand": build_nand_module,
    "indicator": build_indicator_module,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    target = argv[0] if argv else TARGET
    try:
        builder = BUILDERS[target]
    except KeyError:
        sys.exit(f"unknown target {target!r}; choose from {sorted(BUILDERS)}")
    builder()
    print(f"wrote {target}_module.net")


if __name__ == "__main__":
    main()
