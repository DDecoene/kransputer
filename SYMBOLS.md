# Resolved KiCad symbols and footprints

Verified 2026-09-06 against KiCad 10.0.6 bundled libraries.

## Transistors

| Part   | Symbol                  | Footprint                     | Pins (num, name)        |
|--------|-------------------------|-------------------------------|-------------------------|
| BSS84  | `Transistor_FET:BSS84`  | `Package_TO_SOT_SMD:SOT-23`   | 1=G, 2=S, 3=D           |
| BSS138 | `Transistor_FET:BSS138` | `Package_TO_SOT_SMD:SOT-23`   | 1=G, 2=S, 3=D           |

`value` is `"BSS84"` / `"BSS138"` out of the symbol; do not pass `value=`.

## LED

`Device:LED` on `LED_SMD:LED_0805_2012Metric`. Pins: 1=K, 2=A.

## LED series resistor array (indicator board)

**There is no 3x resistor-array footprint in KiCad 10.** Nearest is `4x0603`.
So the indicator board uses one **4-element** array per gate, with the 4th
resistor unused (both pins tied to GND — no current, no floating-pad DRC).

- Footprint: `Resistor_SMD:R_Array_Convex_4x0603` (8 pads)
- Symbol:    `Device:R_Pack04` (8 pins, 4 isolated resistors)
- Pin map: R1 = 1 & 8, R2 = 2 & 7, R3 = 3 & 6, R4 = 4 & 5
- LED-anode side = pads 1/2/3 (one physical edge), VDD side = pads 8/7/6
- `_RARRAY_PAIRS = [("1", "8"), ("2", "7"), ("3", "6")]`  (A, B, Y)
- Spare: `("4", "5")` both to GND

## 16-pin bus header

- Footprint: `Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical`
- Symbol:    `Connector:Conn_01x16_Pin`
- Pins: num `"1"`..`"16"`, name `"Pin_1"`..`"Pin_16"`
- Integer indexing (`j[8]`) resolves by pin number.

## Bulk cap

`Device:C` on `Capacitor_SMD:C_0805_2012Metric`. Pins 1, 2.
