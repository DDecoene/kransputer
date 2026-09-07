import re

import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_gate():
    a, b, y = Net("NOR_1_A"), Net("NOR_1_B"), Net("NOR_1_Y")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.nor_gate(1, a, b, y, vdd, gnd)


def test_nor_gate_has_four_semantic_transistors():
    _one_gate()
    parts = active_circuit().parts
    assert {p.ref for p in parts} == {"QPA1", "QPB1", "QNA1", "QNB1"}
    vals = {p.ref: p.value for p in parts}
    assert vals["QPA1"] == "AO3401A"
    assert vals["QNA1"] == "AO3400A"


def test_nor_gate_topology():
    _one_gate()
    assert pins_named(net_by_name("NOR_1_A")) == {("QPA1", "G"), ("QNA1", "G")}
    assert pins_named(net_by_name("NOR_1_B")) == {("QPB1", "G"), ("QNB1", "G")}
    assert pins_named(net_by_name("VDD")) == {("QPA1", "S")}
    assert pins_named(net_by_name("NOR_1_MID")) == {("QPA1", "D"), ("QPB1", "S")}
    assert pins_named(net_by_name("NOR_1_Y")) == {
        ("QPB1", "D"), ("QNA1", "D"), ("QNB1", "D")}
    assert pins_named(net_by_name("GND")) == {("QNA1", "S"), ("QNB1", "S")}


def test_nor_gate_footprints_are_sot23():
    _one_gate()
    assert all(p.footprint == circuit.FP_SOT23 for p in active_circuit().parts)


def test_assemble_nor_module_part_counts():
    circuit.assemble_nor_module()
    parts = active_circuit().parts
    assert len([p for p in parts if p.value == "AO3401A"]) == 8
    assert len([p for p in parts if p.value == "AO3400A"]) == 8
    assert {p.ref for p in parts if p.ref.startswith("J")} == {"J1", "J2"}
    assert [p.ref for p in parts if p.ref == "C1"] == ["C1"]
    assert not [p for p in parts if p.value == "LED"]


def test_assemble_nor_module_bus_wiring():
    circuit.assemble_nor_module()
    j1 = next(p for p in active_circuit().parts if p.ref == "J1")
    assert j1[5].net.name == "NOR_1_Y"
    assert j1[8].net.name == "NOR_2_Y"
    assert j1[14].net.name == "NOR_4_Y"
    assert pins_numbered(net_by_name("BUS_X")) == {("J1", "15"), ("J2", "15")}


def test_assemble_nor_module_bulk_cap_across_rails():
    circuit.assemble_nor_module()
    assert ("C1", "1") in pins_numbered(net_by_name("VDD"))
    assert ("C1", "2") in pins_numbered(net_by_name("GND"))


def test_build_nor_module_writes_netlist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    circuit.build_nor_module()
    out = tmp_path / "nor_module.net"
    assert out.exists()
    comps = re.findall(r"\(comp\s", out.read_text())
    assert len(comps) == 19   # 16 FET + C1 + J1 + J2
