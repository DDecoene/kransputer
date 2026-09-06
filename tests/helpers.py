"""Inspection helpers for the SKiDL default circuit.

skidl 2.3 injects ``default_circuit`` into Python builtins rather than exposing
it as ``skidl.default_circuit``; reach it through the ``builtins`` module.
"""
import builtins


def circuit():
    """The active SKiDL circuit (skidl 2.3 keeps it in builtins)."""
    return builtins.default_circuit


_circuit = circuit


def part_by_ref(ref):
    for p in _circuit().parts:
        if p.ref == ref:
            return p
    raise KeyError(ref)


def net_by_name(name):
    for n in _circuit().nets:
        if n.name == name:
            return n
    raise KeyError(name)


def pins_named(net):
    """Set of (part ref, pin name) tuples on `net`."""
    return {(p.part.ref, str(p.name)) for p in net.get_pins()}


def pins_numbered(net):
    """Set of (part ref, pin number) tuples on `net`."""
    return {(p.part.ref, str(p.num)) for p in net.get_pins()}
