import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_gate():
    a, b, y = Net("NAND_1_A"), Net("NAND_1_B"), Net("NAND_1_Y")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.indicator_gate(1, a, b, y, vdd, gnd)


def _part(ref):
    return next(p for p in active_circuit().parts if p.ref == ref)


def test_indicator_gate_parts():
    _one_gate()
    refs = {p.ref for p in active_circuit().parts}
    assert {"QA_1", "QB_1", "QY_1"} <= refs   # buffer FETs
    assert {"A_1", "B_1", "Y_1"} <= refs      # LEDs
    assert "RN1" in refs                   # resistor array
    led = _part("A_1")
    assert led.value == "A_1"
    assert led.footprint == circuit.FP_LED


def test_indicator_gate_channel_topology():
    _one_gate()
    # BSS138 common source: source -> GND, gate -> bus signal
    assert ("QB_1", "G") in pins_named(net_by_name("NAND_1_B"))
    assert ("QB_1", "S") in pins_named(net_by_name("GND"))
    # LED cathode ties to the FET drain (private net)
    d, q = _part("B_1"), _part("QB_1")
    assert d["K"].net is q["D"].net
    assert d["K"].net.name not in ("VDD", "GND", "NAND_1_B")
    # LED anode goes to the array
    assert ("RN1", "2") in pins_named(d["A"].net) or \
           ("RN1", "2") in pins_numbered(d["A"].net)


def test_indicator_gate_array_feeds_vdd_and_parks_spare():
    _one_gate()
    vdd = pins_numbered(net_by_name("VDD"))
    gnd = pins_numbered(net_by_name("GND"))
    assert {("RN1", "8"), ("RN1", "7"), ("RN1", "6")} <= vdd   # A,B,Y VDD side
    assert {("RN1", "4"), ("RN1", "5")} <= gnd                 # spare R4 parked


def test_assemble_indicator_module_counts():
    circuit.assemble_indicator_module()
    parts = active_circuit().parts
    assert len([p for p in parts if p.value == "BSS138"]) == 12
    assert len([p for p in parts if p.footprint == circuit.FP_LED]) == 12
    assert sorted(p.ref for p in parts if p.ref.startswith("RN")) == \
        ["RN1", "RN2", "RN3", "RN4"]
    assert {p.ref for p in parts if p.ref.startswith("J")} == {"J1", "J2"}
    assert [p.ref for p in parts if p.ref == "C1"] == ["C1"]
    assert not [p for p in parts if p.value == "BSS84"]


def test_assemble_indicator_module_bus_reaches_buffers():
    circuit.assemble_indicator_module()
    j1 = next(p for p in active_circuit().parts if p.ref == "J1")
    assert j1[10].net.name == "NAND_3_B"                       # bus pin 10
    assert ("QB_3", "G") in pins_named(net_by_name("NAND_3_B"))


def test_build_indicator_module_writes_netlist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    circuit.build_indicator_module()
    assert (tmp_path / "indicator_module.net").exists()
