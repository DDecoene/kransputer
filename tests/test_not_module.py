import re

import circuit
from skidl import Net
from helpers import circuit as active_circuit, net_by_name, pins_named, pins_numbered


def _one_gate():
    vin, vout = Net("NOT_1_IN"), Net("NOT_1_OUT")
    vdd, gnd = Net("VDD"), Net("GND")
    circuit.not_gate(1, vin, vout, vdd, gnd)


def test_not_gate_has_two_semantic_transistors():
    _one_gate()
    parts = active_circuit().parts
    assert {p.ref for p in parts} == {"QP1", "QN1"}
    vals = {p.ref: p.value for p in parts}
    assert vals["QP1"] == "AO3401A"
    assert vals["QN1"] == "AO3400A"


def test_not_gate_topology():
    _one_gate()
    assert pins_named(net_by_name("NOT_1_IN")) == {("QP1", "G"), ("QN1", "G")}
    assert pins_named(net_by_name("VDD")) == {("QP1", "S")}
    assert pins_named(net_by_name("GND")) == {("QN1", "S")}
    assert pins_named(net_by_name("NOT_1_OUT")) == {("QP1", "D"), ("QN1", "D")}


def test_not_gate_footprints_are_sot23():
    _one_gate()
    assert all(p.footprint == circuit.FP_SOT23 for p in active_circuit().parts)


def test_assemble_not_module_part_counts():
    circuit.assemble_not_module()
    parts = active_circuit().parts
    assert len([p for p in parts if p.value == "AO3401A"]) == 6
    assert len([p for p in parts if p.value == "AO3400A"]) == 6
    assert {p.ref for p in parts if p.ref.startswith("J")} == {"J1", "J2"}
    assert [p.ref for p in parts if p.ref == "C1"] == ["C1"]
    assert not [p for p in parts if p.value == "LED"]


def test_assemble_not_module_bus_wiring():
    circuit.assemble_not_module()
    j1 = next(p for p in active_circuit().parts if p.ref == "J1")
    assert j1[3].net.name == "NOT_1_IN"
    assert j1[4].net.name == "NOT_1_OUT"
    assert j1[14].net.name == "NOT_6_OUT"
    assert pins_numbered(net_by_name("BUS_X")) == {("J1", "15"), ("J2", "15")}


def test_assemble_not_module_bulk_cap_across_rails():
    circuit.assemble_not_module()
    assert ("C1", "1") in pins_numbered(net_by_name("VDD"))
    assert ("C1", "2") in pins_numbered(net_by_name("GND"))


def test_build_not_module_writes_netlist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    circuit.build_not_module()
    out = tmp_path / "not_module.net"
    assert out.exists()
    comps = re.findall(r"\(comp\s", out.read_text())
    assert len(comps) == 15   # 12 FET + C1 + J1 + J2
