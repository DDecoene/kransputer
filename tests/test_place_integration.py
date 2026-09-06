"""End-to-end: netlist -> board (kinet2pcb) -> place.py. Skips if tools absent."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VENV_PY = REPO / "venv" / "bin" / "python"
KINET2PCB = REPO / "venv" / "bin" / "kinet2pcb"
KIPY = Path("/Applications/KiCad/KiCad.app/Contents/Frameworks/"
            "Python.framework/Versions/3.9/bin/python3")

pytestmark = pytest.mark.skipif(
    not KIPY.exists() or not KINET2PCB.exists(),
    reason="needs KiCad bundled Python and kinet2pcb",
)


def test_place_lays_out_nand_board(tmp_path):
    env = dict(os.environ)
    subprocess.run([str(VENV_PY), str(REPO / "circuit.py"), "nand"],
                   cwd=tmp_path, check=True, capture_output=True, text=True)

    proj = tmp_path / "nand_module"
    proj.mkdir()
    r = subprocess.run(
        [str(KINET2PCB), "-i", str(tmp_path / "nand_module.net"),
         "-o", str(proj / "nand_module.kicad_pcb"), "-w"],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    if r.returncode != 0 or not (proj / "nand_module.kicad_pcb").exists():
        pytest.skip(f"kinet2pcb unavailable: {(r.stderr or r.stdout)[-400:]}")

    r = subprocess.run(
        [str(KIPY), str(REPO / "place.py"), "nand",
         str(proj / "nand_module.kicad_pcb")],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr

    pcb = (proj / "nand_module.kicad_pcb").read_text()
    ats = [ln.strip() for ln in pcb.splitlines()
           if ln.strip().startswith("(at ")]
    assert ats, "no placed footprints"
    assert not any(a in ("(at 0 0)", "(at 0 0 0)") for a in ats)
    assert '"Edge.Cuts"' in pcb
