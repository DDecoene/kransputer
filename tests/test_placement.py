import placement as pl


def test_grid_positions_row_major():
    pts = pl.grid_positions(3, cols=2, pitch_x_mm=10, pitch_y_mm=8,
                            origin_mm=(0, 0))
    assert pts == [(0, 0), (10, 0), (0, 8)]


def test_grid_positions_empty():
    assert pl.grid_positions(0, 2, 10, 10, (5, 5)) == []


def test_bus_row_ys():
    assert pl.bus_row_ys(22.86, 40.0) == (40.0, 62.86)


def test_header_pin_xs():
    xs = pl.header_pin_xs(16, 2.54, 40.0)
    assert len(xs) == 16
    assert xs[0] == 40.0
    assert xs[-1] == 40.0 + 15 * 2.54


def test_outline_rect_adds_margin():
    rect = pl.outline_rect([(10, 20), (30, 5), (25, 40)], margin_mm=2)
    assert rect == (8, 3, 32, 42)


def test_natural_key_orders_numerically():
    refs = ["Q10", "Q2", "Q1"]
    assert sorted(refs, key=pl.natural_key) == ["Q1", "Q2", "Q10"]


def test_group_by_sheet_defaults_blank_to_root():
    groups = pl.group_by_sheet([("J1", ""), ("Q1", "nand_gate1"),
                                ("Q2", "nand_gate1")])
    assert groups == {"root": ["J1"], "nand_gate1": ["Q1", "Q2"]}
