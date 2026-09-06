"""Inspection helpers for the SKiDL default circuit."""
from skidl import default_circuit


def part_by_ref(ref):
    for p in default_circuit.parts:
        if p.ref == ref:
            return p
    raise KeyError(ref)


def net_by_name(name):
    for n in default_circuit.nets:
        if n.name == name:
            return n
    raise KeyError(name)


def pins_named(net):
    """Set of (part ref, pin name) tuples on `net`."""
    return {(p.part.ref, str(p.name)) for p in net.get_pins()}


def pins_numbered(net):
    """Set of (part ref, pin number) tuples on `net`."""
    return {(p.part.ref, str(p.num)) for p in net.get_pins()}
