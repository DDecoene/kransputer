import pytest

import circuit
from helpers import pins_numbered

SIGNALS = [f"S{i}" for i in range(1, 13)]


def test_bus_pinmap_frames_vdd_gnd_and_spares():
    pm = circuit.bus_pinmap(SIGNALS)
    assert len(pm) == 16
    assert pm[0] == "VDD"
    assert pm[1] == "GND"
    assert pm[2:14] == SIGNALS
    assert pm[-2:] == ["BUS_X", "BUS_Y"]


def test_bus_pinmap_rejects_wrong_signal_count():
    with pytest.raises(ValueError):
        circuit.bus_pinmap(["only", "three", "names"])


def test_add_bus_headers_mirrors_every_pin_on_both_edges():
    j1, j2 = circuit.add_bus_headers({}, SIGNALS)
    assert j1.ref == "J1" and j2.ref == "J2"
    assert j1.footprint == circuit.FP_HDR16
    for k, name in enumerate(circuit.bus_pinmap(SIGNALS), start=1):
        assert j1[k].net.name == name, f"J1 pin {k}"
        assert j2[k].net.name == name, f"J2 pin {k}"


def test_add_bus_headers_reuses_supplied_nets():
    from skidl import Net

    vdd = Net("VDD")
    circuit.add_bus_headers({"VDD": vdd}, SIGNALS)
    assert ("J1", "1") in pins_numbered(vdd)
    assert ("J2", "1") in pins_numbered(vdd)
