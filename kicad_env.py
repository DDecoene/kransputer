"""Point SKiDL at the bundled KiCad libraries on macOS.

Import this module *before* importing skidl (skidl reads KICAD*_SYMBOL_DIR at
import time).
"""
import os
import sys

_KICAD_SHARED = "/Applications/KiCad/KiCad.app/Contents/SharedSupport"

if sys.platform == "darwin" and os.path.exists(_KICAD_SHARED):
    for _v in ["", "6", "7", "8", "9", "10"]:
        os.environ[f"KICAD{_v}_SYMBOL_DIR"] = f"{_KICAD_SHARED}/symbols"
        os.environ[f"KICAD{_v}_FOOTPRINT_DIR"] = f"{_KICAD_SHARED}/footprints"
