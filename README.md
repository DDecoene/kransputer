# kransputer

## What Kransputer is

Kransputer is a working computer built from a few thousand discrete CMOS
transistors — a machine on the scale of an Intel 4004, but made of parts you can
hold — designed to grow into a multiprocessor: one core, then a ring of up to
eight, passing messages the way INMOS's Transputer did. It exists to be
understood and rebuilt, by a person, a class or a hackerspace. Not to be sold.

## Why it looks the way it does

One decision forces everything else: CMOS. Almost every discrete-transistor
computer ever built is NMOS and burns about a watt standing still. CMOS costs
twice the transistors but makes power scale with clock rate instead — turn the
clock down and the machine sips. Staying inside a small transistor budget is why
the design is stripped to the bone:

- **One instruction** — subleq only, so there is no decoder. The instruction set
  lives in the assembler as macros.
- **A few bits at a time** — a serial datapath, so the arithmetic unit is a
  handful of adders. You pay in clock cycles, which are cheap.
- **No bus** — memory, display and input all speak SPI over four wires. No
  address bus, no data bus.

On this machine, talking to the core next door is cheaper than reading your own
memory. That is why the ring is the point, not an afterthought.

## How it gets built — from the ground up

The architecture is settled: the same SUBLEQ core and message-passing ring
already worked out as a Python model. What changes is the direction of the work.
Instead of proving the whole machine in Verilog and on an FPGA before touching a
soldering iron, Kransputer is built upward from real gates, one module at a time,
with the emulator kept alongside as the reference every physical block has to
match.

1. **Gates** — small PCBs, each a fistful of MOSFETs forming one logic function
   (NAND, NOR, NOT …), that plug into a breadboard and share a common bus. This
   is the layer being built now.
2. **Blocks** — those gates wired into the units the design calls for: the serial
   adder that is the whole ALU, the registers, the subleq sequencer and bit
   counter, the SPI interface to memory, the four-wire link to the next core.
3. **A core** — one complete processor, assembled from the blocks.
4. **A ring** — the core replicated and connected: two, then four, then eight,
   blocking on the links for synchronisation.

At every step the hardware is checked against the emulator: same program in, same
answer out, or the block is wrong.

## This repository

Discrete-logic building blocks for the kransputer — the **Gates** layer above.
Each module is a small PCB that plugs into a breadboard on two opposite edge
headers carrying an identical 16-pin pass-through bus, so modules can sit side by
side across one or more breadboards and be wired together into larger logic.

## Boards

| TARGET      | Board                                    |
|-------------|-------------------------------------------|
| `nand`      | 4x discrete static-CMOS 2-input NAND      |
| `nor`       | 4x discrete static-CMOS 2-input NOR       |
| `not`       | 6x discrete static-CMOS inverter          |
| `indicator` | 12-channel buffered bus LED indicator     |

Logic FETs are AO3400A (N-channel) / AO3401A (P-channel) in SOT-23.

The logic boards carry **no** indicator parts. Every node is on the bus; the
indicator board buffers each signal with a single AO3400A in common source (its
gate is high-impedance, so the logic net is not loaded) that sinks an LED fed
from the indicator board's own VDD rail. **LED lit = logic 1.** Watching the
machine therefore does not sag the logic levels.

## Bus pinout

Both edge headers (`J1`, `J2`) carry the same 16 pins, wired 1:1, so any signal
is reachable from either edge. Framing is fixed: pin 1 = VDD, pin 2 = GND,
pins 3–14 carry the 12 signal nets the board drives, pins 15/16 are the
edge-to-edge spares (`BUS_X`, `BUS_Y`).

`J1`/`J2` are stacking headers: male tails point down into the breadboard,
female sockets face up so the indicator shield can plug onto the same 16 pins.

### Signal nets per board (bus pins 3–14)

| Pin | `nand`   | `nor`   | `not`      | `indicator` |
|-----|----------|---------|------------|-------------|
| 3   | NAND_1_A | NOR_1_A | NOT_1_IN   | SIG1        |
| 4   | NAND_1_B | NOR_1_B | NOT_1_OUT  | SIG2        |
| 5   | NAND_1_Y | NOR_1_Y | NOT_2_IN   | SIG3        |
| 6   | NAND_2_A | NOR_2_A | NOT_2_OUT  | SIG4        |
| 7   | NAND_2_B | NOR_2_B | NOT_3_IN   | SIG5        |
| 8   | NAND_2_Y | NOR_2_Y | NOT_3_OUT  | SIG6        |
| 9   | NAND_3_A | NOR_3_A | NOT_4_IN   | SIG7        |
| 10  | NAND_3_B | NOR_3_B | NOT_4_OUT  | SIG8        |
| 11  | NAND_3_Y | NOR_3_Y | NOT_5_IN   | SIG9        |
| 12  | NAND_4_A | NOR_4_A | NOT_5_OUT  | SIG10       |
| 13  | NAND_4_B | NOR_4_B | NOT_6_IN   | SIG11       |
| 14  | NAND_4_Y | NOR_4_Y | NOT_6_OUT  | SIG12       |

The bus is positional: `J1` pin k ≡ `J2` pin k on every board. The indicator
shield taps pins 3–14 as `SIG1..SIG12` and shows whatever a neighbouring board
drives there.

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

Repeat with `nor`, `not`, and `indicator` (each is its own KiCad project in its
own `<target>_module/` folder).

### Fan-out

A discrete gate output driving other **gate** inputs is limited by speed, not
current (CMOS inputs are capacitive) — fine at this machine's speeds. One
indicator-board channel adds roughly the AO3400A gate capacitance to the net it
watches; one indicator board on the bus is negligible.

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
