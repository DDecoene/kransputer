#!/usr/bin/env python3
import os
import sys

# ---- macOS KiCad Fix ------------------------------------------------------
KICAD_APP_PATH = "/Applications/KiCad/KiCad.app/Contents/SharedSupport"
if sys.platform == "darwin" and os.path.exists(KICAD_APP_PATH):
    for v in ["", "6", "7", "8", "9", "10"]:
        os.environ[f"KICAD{v}_SYMBOL_DIR"] = f"{KICAD_APP_PATH}/symbols"
        os.environ[f"KICAD{v}_FOOTPRINT_DIR"] = f"{KICAD_APP_PATH}/footprints"
# ---------------------------------------------------------------------------

from skidl import Part, Net, subcircuit, generate_netlist, set_default_tool, POWER

try:
    from skidl import KICAD8 as KICAD_TOOL
except ImportError:
    try:
        from skidl import KICAD7 as KICAD_TOOL
    except ImportError:
        from skidl import KICAD as KICAD_TOOL

set_default_tool(KICAD_TOOL)

FP_SOT23 = "Package_TO_SOT_SMD:SOT-23"
FP_R     = "Resistor_SMD:R_0805_2012Metric"
FP_LED   = "LED_SMD:LED_0805_2012Metric"
FP_HDR2  = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_HDR3  = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"


@subcircuit
def inverter(vin, vout, vdd, gnd):
    """Pure Static-CMOS inverter (NOT-poort). 0% statisch stroomverbruik."""
    q_p = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    q_n = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)

    vin.connect(q_p['G'], q_n['G'])
    vdd.connect(q_p['S'])             
    gnd.connect(q_n['S'])             
    vout.connect(q_p['D'], q_n['D'])  


@subcircuit
def nand_gate(va, vb, vout, vdd, gnd):
    """Pure Static-CMOS 2-input NAND-poort."""
    qp1 = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    qp2 = Part("Transistor_FET", "BSS84",  footprint=FP_SOT23)
    qn1 = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)
    qn2 = Part("Transistor_FET", "BSS138", footprint=FP_SOT23)
    n_internal = Net()

    va.connect(qp1['G'], qn1['G'])
    vb.connect(qp2['G'], qn2['G'])
    
    vdd.connect(qp1['S'], qp2['S'])
    vout.connect(qp1['D'], qp2['D'], qn1['D'])
    
    n_internal.connect(qn1['S'], qn2['D'])
    gnd.connect(qn2['S'])


@subcircuit
def nor_gate(va, vb, vout, vdd, gnd):
    """Pure Static-CMOS 2-input NOR-poort."""
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
def led_indicator(node, gnd, r_value="470"):
    """LED indicator. Alleen hier is een stroombegrenzende weerstand toegestaan."""
    d = Part("Device", "LED", value="LED",     footprint=FP_LED)
    r = Part("Device", "R",   value=r_value,   footprint=FP_R)

    node.connect(d['A'])
    gnd.connect(r['2'])
    Net().connect(d['K'], r['1'])


def build():
    vdd, gnd = Net("VDD"), Net("GND")
    vdd.drive = POWER; gnd.drive = POWER

    # Hoofdvoeding
    j_pwr = Part("Connector", "Conn_01x02_Pin", value="MAIN_PWR", footprint=FP_HDR2)
    vdd.connect(j_pwr['1'])
    gnd.connect(j_pwr['2'])

    # --- 1. NOT ---
    vin_not, vout_not = Net("NOT_IN"), Net("NOT_OUT")
    j_not = Part("Connector", "Conn_01x02_Pin", value="CONN_NOT", footprint=FP_HDR2)
    vin_not.connect(j_not['1'])
    vout_not.connect(j_not['2'])

    inverter(vin_not, vout_not, vdd, gnd)
    led_indicator(vout_not, gnd, "470")

    # --- 2. NAND ---
    va_nand, vb_nand, vout_nand = Net("NAND_A"), Net("NAND_B"), Net("NAND_OUT")
    j_nand = Part("Connector", "Conn_01x03_Pin", value="CONN_NAND", footprint=FP_HDR3)
    va_nand.connect(j_nand['1'])
    vb_nand.connect(j_nand['2'])
    vout_nand.connect(j_nand['3'])

    nand_gate(va_nand, vb_nand, vout_nand, vdd, gnd)
    led_indicator(vout_nand, gnd, "470")

    # --- 3. NOR ---
    va_nor, vb_nor, vout_nor = Net("NOR_A"), Net("NOR_B"), Net("NOR_OUT")
    j_nor = Part("Connector", "Conn_01x03_Pin", value="CONN_NOR", footprint=FP_HDR3)
    va_nor.connect(j_nor['1'])
    vb_nor.connect(j_nor['2'])
    vout_nor.connect(j_nor['3'])

    nor_gate(va_nor, vb_nor, vout_nor, vdd, gnd)
    led_indicator(vout_nor, gnd, "470")

    print("Netlist genereren...")
    generate_netlist(file_="logic_gates_project.net", do_backup=False)
    print("Netlist succesvol aangemaakt zonder overbodige weerstanden!")


if __name__ == "__main__":
    build()
