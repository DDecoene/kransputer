def test_skidl_imports_with_kicad_libs():
    import circuit  # noqa: F401  - triggers the macOS KiCad path fix on import
    from skidl import Part

    r = Part("Device", "R", value="1k", footprint="Resistor_SMD:R_0603_1608Metric")
    assert r["1"] is not None
    assert r["2"] is not None
