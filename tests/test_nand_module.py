import re

import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_gate():
    a, b, y = Net("NAND_1_A"), Net("NAND_1_B"), Net("NAND_1_Y")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.nand_gate(1, a, b, y, vdd, gnd)


def test_nand_gate_has_four_semantic_transistors():
    _one_gate()
    parts = active_circuit().parts
    refs = {p.ref for p in parts}
    assert refs == {"QPA_1", "QPB_1", "QNA_1", "QNB_1"}
    vals = {p.ref: p.value for p in parts}
    assert vals["QPA_1"] == "BSS84"
    assert vals["QNA_1"] == "BSS138"


def test_nand_gate_topology():
    _one_gate()
    assert pins_named(net_by_name("NAND_1_A")) == {("QPA_1", "G"), ("QNA_1", "G")}
    assert pins_named(net_by_name("NAND_1_B")) == {("QPB_1", "G"), ("QNB_1", "G")}
    assert pins_named(net_by_name("VDD")) == {("QPA_1", "S"), ("QPB_1", "S")}
    assert pins_named(net_by_name("NAND_1_Y")) == {
        ("QPA_1", "D"), ("QPB_1", "D"), ("QNA_1", "D")}
    assert pins_named(net_by_name("NAND_1_MID")) == {
        ("QNA_1", "S"), ("QNB_1", "D")}
    assert pins_named(net_by_name("GND")) == {("QNB_1", "S")}


def test_nand_gate_footprints_are_sot23():
    _one_gate()
    assert all(p.footprint == circuit.FP_SOT23
               for p in active_circuit().parts)


def test_assemble_nand_module_part_counts():
    circuit.assemble_nand_module()
    parts = active_circuit().parts
    assert len([p for p in parts if p.value == "BSS84"]) == 8
    assert len([p for p in parts if p.value == "BSS138"]) == 8
    assert {p.ref for p in parts if p.ref.startswith("J")} == {"J1", "J2"}
    assert [p.ref for p in parts if p.ref == "C1"] == ["C1"]
    assert not [p for p in parts if p.value == "LED"]


def test_assemble_nand_module_bus_wiring():
    circuit.assemble_nand_module()
    j1 = next(p for p in active_circuit().parts if p.ref == "J1")
    assert j1[5].net.name == "NAND_1_Y"
    assert j1[8].net.name == "NAND_2_Y"
    assert j1[14].net.name == "NAND_4_Y"
    assert pins_numbered(net_by_name("BUS_X")) == {("J1", "15"), ("J2", "15")}


def test_assemble_nand_module_bulk_cap_across_rails():
    circuit.assemble_nand_module()
    assert ("C1", "1") in pins_numbered(net_by_name("VDD"))
    assert ("C1", "2") in pins_numbered(net_by_name("GND"))


def test_build_nand_module_writes_netlist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    circuit.build_nand_module()
    out = tmp_path / "nand_module.net"
    assert out.exists()
    comps = re.findall(r"\(comp\s", out.read_text())
    assert len(comps) == 19   # 16 FET + C1 + J1 + J2
