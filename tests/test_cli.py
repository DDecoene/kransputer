import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = REPO / "venv" / "bin" / "python"


def _run(args, cwd):
    return subprocess.run([str(PY), str(REPO / "circuit.py"), *args],
                          cwd=cwd, capture_output=True, text=True)


def test_no_argument_builds_every_module(tmp_path):
    r = _run([], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "nand_module.net").exists()
    assert (tmp_path / "indicator_module.net").exists()


def test_explicit_single_target(tmp_path):
    r = _run(["indicator"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "indicator_module.net").exists()
    assert not (tmp_path / "nand_module.net").exists()


def test_unknown_target_exits_nonzero(tmp_path):
    r = _run(["bogus"], tmp_path)
    assert r.returncode != 0
    assert "unknown target" in (r.stderr + r.stdout)


def test_no_argument_builds_nor_and_not(tmp_path):
    r = _run([], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "nor_module.net").exists()
    assert (tmp_path / "not_module.net").exists()


def test_explicit_nor_target_only(tmp_path):
    r = _run(["nor"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "nor_module.net").exists()
    assert not (tmp_path / "nand_module.net").exists()


def test_explicit_not_target_only(tmp_path):
    r = _run(["not"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "not_module.net").exists()
    assert not (tmp_path / "nand_module.net").exists()
