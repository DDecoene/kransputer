"""Shared pytest fixtures for the SKiDL generator tests."""
import kicad_env  # noqa: F401  - must precede any skidl import

import pytest

try:  # skidl 2.3 exposes reset() at package level
    from skidl import reset as _skidl_reset
except ImportError:  # pragma: no cover - fallback for other versions
    from skidl import default_circuit

    def _skidl_reset():
        default_circuit.reset()


@pytest.fixture(autouse=True)
def reset_skidl():
    """Every test starts and ends with an empty default circuit."""
    _skidl_reset()
    yield
    _skidl_reset()
