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
