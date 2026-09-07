#!/usr/bin/env python3
"""Generate KiCad netlists for the kransputer bus modules.

Each module is a breadboard-pluggable board that carries an identical 16-pin
pass-through bus on two opposite edge headers.

TARGET (or argv[1]) selects the board:
  nand       4x discrete static-CMOS 2-input NAND gate
  nor        4x discrete static-CMOS 2-input NOR gate
  not        6x discrete static-CMOS inverter
  indicator  12-channel buffered bus LED indicator (generic SIG1..SIG12 taps)

Output: <target>_module.net
"""
import sys

import kicad_env  # noqa: F401  - points skidl at the KiCad libs; keep before skidl

from skidl import (
    Part, Net, subcircuit, generate_netlist, set_default_tool, reset, POWER,
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

# ---- Default MOSFETs -----------------------------------------------------
# Static-CMOS logic FETs. AO3400A / AO3401A are drop-in for BSS138 / BSS84:
# same Transistor_FET base symbols (pin 1=G, 2=S, 3=D) and SOT-23 footprint.
FET_N = "AO3400A"   # N-channel  (was BSS138)
FET_P = "AO3401A"   # P-channel  (was BSS84)

# ---- Values ----------------------------------------------------------------
LED_R  = "1k"   # LED series resistor on the indicator board (2k2 = softer)
BULK_C = "1u"   # per-board bulk decoupling

# ---- Bus ----------------------------------------------------------------
# 16-pin pass-through bus, identical on both edge headers (J1 pin k == J2 pin k).
# Framing is fixed: pin 1 = VDD, pin 2 = GND, pins 3..14 carry the 12 signal
# nets a board supplies, pins 15/16 are the edge-to-edge spares.
BUS_SPARES = ["BUS_X", "BUS_Y"]


def bus_pinmap(signals):
    """Full 16-entry bus net-name list for `signals` (exactly 12, pins 3..14)."""
    if len(signals) != 12:
        raise ValueError(f"bus needs 12 signal names, got {len(signals)}")
    return ["VDD", "GND", *signals, *BUS_SPARES]


def add_bus_headers(nets, signals):
    """Create edge headers J1/J2 and wire every pin to its bus net.

    `signals` is the board's 12 signal net names in pin order (bus pins 3..14).
    `nets` maps bus-net name -> Net; names not present get a fresh Net (used for
    the spare BUS_X/BUS_Y lines on boards that do not drive them).
    Returns (j1, j2).
    """
    pinmap = bus_pinmap(signals)
    for name in pinmap:
        nets.setdefault(name, Net(name))
    # J1/J2 are stacking headers: male tails down into the breadboard, female
    # sockets up for the indicator shield. Same 1x16 THT drill pattern.
    j1 = Part("Connector", "Conn_01x16_Pin", ref="J1", value="BUS_STACK_1x16",
              footprint=FP_HDR16)
    j2 = Part("Connector", "Conn_01x16_Pin", ref="J2", value="BUS_STACK_1x16",
              footprint=FP_HDR16)
    for k, name in enumerate(pinmap, start=1):
        nets[name] += j1[k], j2[k]
    return j1, j2


# ---- Gate subcircuits ----------------------------------------------------


@subcircuit
def nand_gate(n, a, b, y, vdd, gnd):
    """Discrete static-CMOS 2-input NAND gate `n` (1..4).

    The whole board is NAND, so refs drop the redundant prefix: QPA<n>/QPB<n>
    are the parallel AO3401A pull-up, QNA<n>/QNB<n> the series AO3400A pull-down
    through internal node NAND_<n>_MID.
    """
    qpa = Part("Transistor_FET", FET_P, ref=f"QPA{n}", footprint=FP_SOT23)
    qpb = Part("Transistor_FET", FET_P, ref=f"QPB{n}", footprint=FP_SOT23)
    qna = Part("Transistor_FET", FET_N, ref=f"QNA{n}", footprint=FP_SOT23)
    qnb = Part("Transistor_FET", FET_N, ref=f"QNB{n}", footprint=FP_SOT23)
    mid = Net(f"NAND_{n}_MID")

    a   += qpa["G"], qna["G"]
    b   += qpb["G"], qnb["G"]
    vdd += qpa["S"], qpb["S"]
    y   += qpa["D"], qpb["D"], qna["D"]
    mid += qna["S"], qnb["D"]
    gnd += qnb["S"]


@subcircuit
def nor_gate(n, a, b, y, vdd, gnd):
    """Discrete static-CMOS 2-input NOR gate `n` (1..4).

    The whole board is NOR, so refs drop the redundant prefix: QPA<n>/QPB<n> are
    the series AO3401A pull-up through internal node NOR_<n>_MID, QNA<n>/QNB<n>
    the parallel AO3400A pull-down.
    """
    qpa = Part("Transistor_FET", FET_P, ref=f"QPA{n}", footprint=FP_SOT23)
    qpb = Part("Transistor_FET", FET_P, ref=f"QPB{n}", footprint=FP_SOT23)
    qna = Part("Transistor_FET", FET_N, ref=f"QNA{n}", footprint=FP_SOT23)
    qnb = Part("Transistor_FET", FET_N, ref=f"QNB{n}", footprint=FP_SOT23)
    mid = Net(f"NOR_{n}_MID")

    a   += qpa["G"], qna["G"]
    b   += qpb["G"], qnb["G"]
    vdd += qpa["S"]
    mid += qpa["D"], qpb["S"]
    y   += qpb["D"], qna["D"], qnb["D"]
    gnd += qna["S"], qnb["S"]


@subcircuit
def not_gate(n, vin, vout, vdd, gnd):
    """Discrete static-CMOS inverter `n` (1..6).

    QP<n> is the AO3401A pull-up, QN<n> the AO3400A pull-down; both gates driven
    by NOT_<n>_IN, drains tied at NOT_<n>_OUT.
    """
    qp = Part("Transistor_FET", FET_P, ref=f"QP{n}", footprint=FP_SOT23)
    qn = Part("Transistor_FET", FET_N, ref=f"QN{n}", footprint=FP_SOT23)

    vin  += qp["G"], qn["G"]
    vdd  += qp["S"]
    gnd  += qn["S"]
    vout += qp["D"], qn["D"]


# ---- Board assemblies ----------------------------------------------------


NAND_SIGNALS = [f"NAND_{n}_{p}" for n in range(1, 5) for p in ("A", "B", "Y")]
NOR_SIGNALS = [f"NOR_{n}_{p}" for n in range(1, 5) for p in ("A", "B", "Y")]
NOT_SIGNALS = [f"NOT_{n}_{p}" for n in range(1, 7) for p in ("IN", "OUT")]
INDICATOR_SIGNALS = [f"SIG{i}" for i in range(1, 13)]


def _nets_from_names(names):
    """{name: Net(name)} for every name in `names`."""
    return {n: Net(n) for n in names}


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
    sig = _nets_from_names(NAND_SIGNALS)
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for n in range(1, 5):
        nand_gate(
            n,
            sig[f"NAND_{n}_A"], sig[f"NAND_{n}_B"], sig[f"NAND_{n}_Y"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets, NAND_SIGNALS)


def build_nand_module():
    assemble_nand_module()
    generate_netlist(file_="nand_module.net", do_backup=False)


# ---- NOR board --------------------------------------------------------------


def assemble_nor_module():
    """4x nor_gate + bulk cap + bus headers. Operates on the default circuit."""
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER
    gnd.drive = POWER
    sig = _nets_from_names(NOR_SIGNALS)
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for n in range(1, 5):
        nor_gate(
            n,
            sig[f"NOR_{n}_A"], sig[f"NOR_{n}_B"], sig[f"NOR_{n}_Y"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets, NOR_SIGNALS)


def build_nor_module():
    assemble_nor_module()
    generate_netlist(file_="nor_module.net", do_backup=False)


# ---- NOT board --------------------------------------------------------------


def assemble_not_module():
    """6x not_gate + bulk cap + bus headers. Operates on the default circuit."""
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER
    gnd.drive = POWER
    sig = _nets_from_names(NOT_SIGNALS)
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for n in range(1, 7):
        not_gate(
            n,
            sig[f"NOT_{n}_IN"], sig[f"NOT_{n}_OUT"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets, NOT_SIGNALS)


def build_not_module():
    assemble_not_module()
    generate_netlist(file_="not_module.net", do_backup=False)


# ---- Indicator board ----------------------------------------------------

# (LED-anode-side pin, VDD-side pin) for each Device:R_Pack04 resistor used by
# a channel; the 4th resistor (pins 4 & 5) is parked on GND. See SYMBOLS.md.
_RARRAY_PAIRS = [("1", "8"), ("2", "7"), ("3", "6")]
_RARRAY_SPARE = ("4", "5")


@subcircuit
def indicator_gate(g, sig_1, sig_2, sig_3, vdd, gnd):
    """Three buffered LED indicators for bus group `g` (1..4).

    Per channel an AO3400A in common source (gate = bus signal, high impedance,
    so the logic net is not loaded) sinks an LED whose anode is fed from VDD
    through one element of the RN<g> array. LED lit = logic 1.

    Refs use a running 1..12 index i = (g - 1) * 3 + c: buffer FETs Q<i>, LEDs
    D<i>, resistor array RN<g>.
    """
    rn = Part("Device", "R_Pack04", ref=f"RN{g}", value=LED_R,
              footprint=FP_RARRAY)
    for (led_pin, vdd_pin), c, signal in zip(
        _RARRAY_PAIRS, (1, 2, 3), (sig_1, sig_2, sig_3)
    ):
        i = (g - 1) * 3 + c
        q = Part("Transistor_FET", FET_N, ref=f"Q{i}", footprint=FP_SOT23)
        d = Part("Device", "LED", ref=f"D{i}", value=f"D{i}", footprint=FP_LED)
        vdd    += rn[vdd_pin]
        gnd    += q["S"]
        signal += q["G"]
        d["K"] += q["D"]
        d["A"] += rn[led_pin]
    # park the unused 4th resistor so its pads are not left floating
    gnd += rn[_RARRAY_SPARE[0]], rn[_RARRAY_SPARE[1]]


def assemble_indicator_module():
    """12 buffered LEDs (4 groups x 3 SIG channels) + bulk cap + bus headers."""
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER
    gnd.drive = POWER
    sig = _nets_from_names(INDICATOR_SIGNALS)
    nets = {"VDD": vdd, "GND": gnd, **sig}

    for g in range(1, 5):
        base = (g - 1) * 3
        indicator_gate(
            g,
            sig[f"SIG{base + 1}"], sig[f"SIG{base + 2}"], sig[f"SIG{base + 3}"],
            vdd, gnd,
        )

    _bulk_cap(vdd, gnd)
    add_bus_headers(nets, INDICATOR_SIGNALS)


def build_indicator_module():
    assemble_indicator_module()
    generate_netlist(file_="indicator_module.net", do_backup=False)


# ---- Entry point ------------------------------------------------------------

BUILDERS = {
    "nand": build_nand_module,
    "indicator": build_indicator_module,
    "nor": build_nor_module,
    "not": build_not_module,
}


def main(argv=None):
    """No argument: build every module netlist. One argument: just that one."""
    argv = sys.argv[1:] if argv is None else list(argv)
    targets = argv or list(BUILDERS)
    unknown = [t for t in targets if t not in BUILDERS]
    if unknown:
        sys.exit(f"unknown target(s) {unknown}; choose from {sorted(BUILDERS)}")
    for target in targets:
        reset()   # each module is generated from a clean circuit
        BUILDERS[target]()
        print(f"wrote {target}_module.net")


if __name__ == "__main__":
    main()
