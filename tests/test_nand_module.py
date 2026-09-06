import re

import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_gate():
    a, b, y = Net("NAND_1_A"), Net("NAND_1_B"), Net("NAND_1_Y")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.nand_gate("NAND_1", a, b, y, vdd, gnd)


def test_nand_gate_has_four_semantic_transistors():
    _one_gate()
    parts = active_circuit().parts
    refs = {p.ref for p in parts}
    assert refs == {"NAND_1_QPA", "NAND_1_QPB", "NAND_1_QNA", "NAND_1_QNB"}
    vals = {p.ref: p.value for p in parts}
    assert vals["NAND_1_QPA"] == "BSS84"
    assert vals["NAND_1_QNA"] == "BSS138"


def test_nand_gate_topology():
    _one_gate()
    assert pins_named(net_by_name("NAND_1_A")) == {
        ("NAND_1_QPA", "G"), ("NAND_1_QNA", "G")}
    assert pins_named(net_by_name("NAND_1_B")) == {
        ("NAND_1_QPB", "G"), ("NAND_1_QNB", "G")}
    assert pins_named(net_by_name("VDD")) == {
        ("NAND_1_QPA", "S"), ("NAND_1_QPB", "S")}
    assert pins_named(net_by_name("NAND_1_Y")) == {
        ("NAND_1_QPA", "D"), ("NAND_1_QPB", "D"), ("NAND_1_QNA", "D")}
    assert pins_named(net_by_name("NAND_1_MID")) == {
        ("NAND_1_QNA", "S"), ("NAND_1_QNB", "D")}
    assert pins_named(net_by_name("GND")) == {("NAND_1_QNB", "S")}


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
