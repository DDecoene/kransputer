import circuit
from helpers import net_by_name, pins_numbered


def test_bus_list_is_16_pins_vdd_gnd_first():
    assert len(circuit.BUS) == 16
    assert circuit.BUS[0] == "VDD"
    assert circuit.BUS[1] == "GND"
    assert circuit.BUS[-2:] == ["BUS_X", "BUS_Y"]


def test_add_bus_headers_mirrors_every_pin_on_both_edges():
    j1, j2 = circuit.add_bus_headers({})
    assert j1.ref == "J1" and j2.ref == "J2"
    assert j1.footprint == circuit.FP_HDR16
    for k, name in enumerate(circuit.BUS, start=1):
        assert j1[k].net.name == name, f"J1 pin {k}"
        assert j2[k].net.name == name, f"J2 pin {k}"


def test_add_bus_headers_reuses_supplied_nets():
    from skidl import Net

    vdd = Net("VDD")
    circuit.add_bus_headers({"VDD": vdd})
    assert ("J1", "1") in pins_numbered(vdd)
    assert ("J2", "1") in pins_numbered(vdd)
