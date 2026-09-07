# Contributing

Contributions are welcome — bug reports, board fixes, new modules, better docs.

## Workflow

1. Open an issue describing what you want to change before large work.
2. Fork, branch, make focused commits.
3. Run the test suite before opening a PR:
   ```bash
   ./venv/bin/pytest
   ```
   Netlist topology for every board type is checked from the SKiDL netlist. New
   or changed modules need matching tests in `tests/`.
4. Keep code and comments in English. Follow the style already in `circuit.py`
   and `place.py`: exact per-board data, small focused functions, semantic
   reference designators set via SKiDL `ref=`.

## Licensing of contributions

By submitting a contribution you agree that:

1. Your contribution is licensed to the project under the same
   [PolyForm Noncommercial License 1.0.0](LICENSE) that covers the rest of the
   project; **and**
2. You grant Dennis Decoene (the maintainer) a perpetual, worldwide,
   non-exclusive, irrevocable, royalty-free licence to use, reproduce, modify,
   and distribute your contribution **for any purpose, including commercial
   purposes** such as selling kits or hardware.

You keep the copyright to your contribution. Point 2 exists so the maintainer can
keep offering kits that may include contributed code or board changes, as
described in [COMMERCIAL.md](COMMERCIAL.md). If you cannot agree to this, please
do not submit a contribution.
