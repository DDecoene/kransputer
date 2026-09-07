import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_group():
    s1, s2, s3 = Net("SIG1"), Net("SIG2"), Net("SIG3")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.indicator_gate(1, s1, s2, s3, vdd, gnd)


def _part(ref):
    return next(p for p in active_circuit().parts if p.ref == ref)


def test_indicator_group_parts():
    _one_group()
    refs = {p.ref for p in active_circuit().parts}
    assert {"Q1", "Q2", "Q3"} <= refs   # buffer FETs, running index
    assert {"D1", "D2", "D3"} <= refs   # LEDs
    assert "RN1" in refs                # resistor array for the group
    led = _part("D1")
    assert led.value == "D1"
    assert led.footprint == circuit.FP_LED
    assert _part("Q1").value == "AO3400A"


def test_indicator_group_channel_topology():
    _one_group()
    # AO3400A common source: source -> GND, gate -> bus signal
    assert ("Q2", "G") in pins_named(net_by_name("SIG2"))
    assert ("Q2", "S") in pins_named(net_by_name("GND"))
    # LED cathode ties to the FET drain (private net)
    d, q = _part("D2"), _part("Q2")
    assert d["K"].net is q["D"].net
    assert d["K"].net.name not in ("VDD", "GND", "SIG2")
    # LED anode goes to the array
    assert ("RN1", "2") in pins_named(d["A"].net) or \
           ("RN1", "2") in pins_numbered(d["A"].net)


def test_indicator_group_array_feeds_vdd_and_parks_spare():
    _one_group()
    vdd = pins_numbered(net_by_name("VDD"))
    gnd = pins_numbered(net_by_name("GND"))
    assert {("RN1", "8"), ("RN1", "7"), ("RN1", "6")} <= vdd   # 3 channels VDD side
    assert {("RN1", "4"), ("RN1", "5")} <= gnd                 # spare R4 parked


def test_second_group_continues_the_running_index():
    s4, s5, s6 = Net("SIG4"), Net("SIG5"), Net("SIG6")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.indicator_gate(2, s4, s5, s6, vdd, gnd)
    refs = {p.ref for p in active_circuit().parts}
    assert {"Q4", "Q5", "Q6", "D4", "D5", "D6", "RN2"} <= refs
    assert ("Q5", "G") in pins_named(net_by_name("SIG5"))


def test_assemble_indicator_module_counts():
    circuit.assemble_indicator_module()
    parts = active_circuit().parts
    assert len([p for p in parts if p.value == "AO3400A"]) == 12
    assert len([p for p in parts if p.footprint == circuit.FP_LED]) == 12
    assert sorted(p.ref for p in parts if p.ref.startswith("RN")) == \
        ["RN1", "RN2", "RN3", "RN4"]
    assert sorted((p.ref for p in parts if p.ref.startswith("D")),
                  key=lambda r: int(r[1:])) == [f"D{i}" for i in range(1, 13)]
    assert {p.ref for p in parts if p.ref.startswith("J")} == {"J1", "J2"}
    assert [p.ref for p in parts if p.ref == "C1"] == ["C1"]
    assert not [p for p in parts if p.value == "AO3401A"]


def test_assemble_indicator_module_bus_reaches_buffers():
    circuit.assemble_indicator_module()
    j1 = next(p for p in active_circuit().parts if p.ref == "J1")
    assert j1[10].net.name == "SIG8"                    # bus pin 10 -> SIG(10-2)
    assert ("Q8", "G") in pins_named(net_by_name("SIG8"))


def test_build_indicator_module_writes_netlist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    circuit.build_indicator_module()
    assert (tmp_path / "indicator_module.net").exists()
