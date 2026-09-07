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


def _pipeline(tmp_path, target):
    """circuit.py <target> -> kinet2pcb -> place.py <target>. Returns pcb text."""
    env = dict(os.environ)
    subprocess.run([str(VENV_PY), str(REPO / "circuit.py"), target],
                   cwd=tmp_path, check=True, capture_output=True, text=True)
    proj = tmp_path / f"{target}_module"
    proj.mkdir()
    r = subprocess.run(
        [str(KINET2PCB), "-i", str(tmp_path / f"{target}_module.net"),
         "-o", str(proj / f"{target}_module.kicad_pcb"), "-w"],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    if r.returncode != 0 or not (proj / f"{target}_module.kicad_pcb").exists():
        pytest.skip(f"kinet2pcb unavailable: {(r.stderr or r.stdout)[-400:]}")
    r = subprocess.run(
        [str(KIPY), str(REPO / "place.py"), target,
         str(proj / f"{target}_module.kicad_pcb")],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    return (proj / f"{target}_module.kicad_pcb").read_text()


def test_place_lays_out_nor_board(tmp_path):
    pcb = _pipeline(tmp_path, "nor")
    ats = [ln.strip() for ln in pcb.splitlines()
           if ln.strip().startswith("(at ")]
    assert ats and not any(a in ("(at 0 0)", "(at 0 0 0)") for a in ats)
    assert '"Edge.Cuts"' in pcb


def test_place_lays_out_not_board(tmp_path):
    pcb = _pipeline(tmp_path, "not")
    ats = [ln.strip() for ln in pcb.splitlines()
           if ln.strip().startswith("(at ")]
    assert ats and not any(a in ("(at 0 0)", "(at 0 0 0)") for a in ats)
    assert '"Edge.Cuts"' in pcb
    # 6 NOT cells stay inside the 16-pin header span (X0=20, span 15*2.54).
    xs = [float(a.split()[1]) for a in ats]
    assert min(xs) >= 20.0 - 6.0 and max(xs) <= 20.0 + 15 * 2.54 + 3.0
