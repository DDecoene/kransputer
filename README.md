# kransputer

Discrete-logic building blocks for the kransputer. Each module is a small PCB
that plugs into a breadboard on two opposite edge headers carrying an identical
16-pin pass-through bus, so modules can sit side by side across one or more
breadboards and be wired together into larger logic.

## Boards

| TARGET      | Board                                    |
|-------------|-------------------------------------------|
| `nand`      | 4x discrete static-CMOS 2-input NAND      |
| `indicator` | 12-channel buffered bus LED indicator     |

The logic boards carry **no** indicator parts. Every node is on the bus; the
indicator board buffers each signal with a single BSS138 in common source (its
gate is high-impedance, so the logic net is not loaded) that sinks an LED fed
from the indicator board's own VDD rail. **LED lit = logic 1.** Watching the
machine therefore does not sag the logic levels.

## Bus pinout

Both edge headers (`J1`, `J2`) carry the same 16 nets, wired 1:1, so any signal
is reachable from either edge.

| Pin | Net      | Pin | Net      |
|-----|----------|-----|----------|
| 1   | VDD      | 9   | NAND_3_A |
| 2   | GND      | 10  | NAND_3_B |
| 3   | NAND_1_A | 11  | NAND_3_Y |
| 4   | NAND_1_B | 12  | NAND_4_A |
| 5   | NAND_1_Y | 13  | NAND_4_B |
| 6   | NAND_2_A | 14  | NAND_4_Y |
| 7   | NAND_2_B | 15  | BUS_X (spare, edge-to-edge only) |
| 8   | NAND_2_Y | 16  | BUS_Y (spare, edge-to-edge only) |

Supply: 5 V on the bus. The two header rows are 0.9" apart (row `a` to row `j`
of one breadboard); columns b–e and f–i stay free for patch wires.

## Build

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

./venv/bin/python circuit.py             # writes every <target>_module.net
./venv/bin/python circuit.py nand        # or just one
```

1. In KiCad: new PCB project `nand_module/`, import `nand_module.net`, save,
   close the board.
2. Rough auto-placement — run from the folder that contains `nand_module/`,
   using KiCad's bundled Python (pcbnew is not in the venv):
   ```bash
   /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
       place.py nand
   ```
   `place.py` positions J1/J2 on opposite edges, clusters each gate between
   them, and draws a tight `Edge.Cuts` rectangle. Pass an explicit
   `.kicad_pcb` path as a second argument to place a board elsewhere.
3. Reopen in KiCad, nudge, route. Pour a GND zone on `B.Cu`. Run DRC.
4. Plot Gerbers.

Repeat with `indicator`.

### Fan-out

A discrete gate output driving other **gate** inputs is limited by speed, not
current (CMOS inputs are capacitive) — fine at this machine's speeds. One
indicator-board channel adds roughly the BSS138 gate capacitance (~50 pF) to
the net it watches; one indicator board on the bus is negligible.

## Tests

```bash
./venv/bin/pytest
```

The placement integration test is skipped unless `kinet2pcb` can import
`pcbnew` (it cannot from the venv). `place.py` uses fixed, hand-computed
coordinates per board type, so its output is deterministic and easy to
eyeball in KiCad.

## Layout

- `circuit.py`  — SKiDL netlist generator (all boards, no arg = build every one)
- `place.py`    — pcbnew layout: exact positions per board type + Edge.Cuts
- `kicad_env.py`— points SKiDL at the bundled KiCad libraries on macOS
- `SYMBOLS.md`  — resolved KiCad symbols and the resistor-array pin map
