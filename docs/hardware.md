# Hardware

## Board

| Part | Identification | Role |
|---|---|---|
| ME32F031C8T6 | MESILICON Cortex-M0, LQFP-48, STM32F030C8T6 drop-in | heater controller |
| BT3L | Tuya BLE module, TLSR8250F512ET32, 512 KB / 48 KB | BLE ↔ UART bridge (removed for Tier 2) |
| WTN6170-8S | Waytronic WTN6 voice chip | beeps / voice prompts |
| CMT2220LS | CMT22xx RF receiver | 433 MHz handheld remote |
| HT1621-class | segment LCD driver | display |

```
433 fob ─► CMT2220 ─┐
sensors ───────────┼─► ME32F031 ─► LCD driver ─► display
                   │      │
                   │      ├─► WTN6170 ─► speaker
                   │      ├─► UART (55 AA) ─► BT3L ══ BLE ══► phone
                   │      └─► UART (Modbus) ─► burner
```

Two separate UARTs — do not confuse them:

- **Tuya MCU** (`55 AA …`) — to the BLE module, 9600 8N1, separate TX and RX
- **Modbus RTU** — to the burner, 9600 8N1, single data wire, controller is master

## BT3L pinout

The module is 16 × 24 mm, 16 pins.

| Pin | Symbol | Function |
|---|---|---|
| 1 | RST | hardware reset, active low |
| 2 | ADC | 12-bit ADC (TL_C4) |
| 3 | NC | — |
| 4 | TL_D7 | GPIO |
| 5 | TL_D2 | GPIO / PWM |
| 6 | TL_C3 | GPIO / PWM |
| 7 | TL_C2 | GPIO / PWM |
| 8 | VDD_BAT | 3.3 V |
| 9 | GND | ground |
| 10 | TL_C0 | GPIO |
| 11 | SWS | single-wire debug |
| 12 | TL_A0 | GPIO |
| 13 | TL_B4 | GPIO / PWM |
| 14 | TL_B5 | GPIO / PWM |
| 15 | TL_B7 | **UART RX** (into module) |
| 16 | TL_B1 | **UART TX** (out of module) |

VDD (8) and GND (9) are adjacent — use that pair to orient the module, then count
to 15/16.

### Footprint orientation (measured on a real board)

Pad numbering runs **counter-clockwise**, not the corner-to-corner way it first
appears:

```
top row    16  15  14  13  12  11  10   9     9  = GND
            .   .   .   .   .   .   .   .
           +----+----+----+----+----+----+----+
           |  B T 3 L   m o d u l e   f o o t  |
           +----+----+----+----+----+----+----+
            .   .   .   .   .   .   .   .
bottom row  1   2   3   4   5   6   7   8     8  = VDD (3.3 V measured)
```

- **8** VDD (3.3 V, confirmed with a meter against the PSU rail)
- **9** GND
- **15** UART RX — from the MCU
- **16** UART TX — to the MCU

That places VDD and GND diagonally adjacent at the right-hand end, which is the
anchor for orienting a replacement.

### SWD

**PA13 = SWDIO**, **PA14 = SWCLK**, both brought out to test points. Handy for
re-dumping or recovering the board without hunting for a header.

Direction matters:

- pin 15 receives **from the MCU** → this net is MCU TX
- pin 16 transmits **to the MCU** → this net is MCU RX

## Removing the BT3L (Tier 2 only)

Needed only if you want to *transmit* — that is, control the heater. The module's
pin 16 drives the MCU's RX line, so two transmitters would collide.

Options, easiest first:

1. **Hot air the module off.** ~330 °C, low flow, plenty of flux. The pads are
   then exposed and easy to solder to. This is the recommended route.
2. **Lift pin 16 only.** Frees the MCU RX net, but you still solder to that pad.
   Fiddly, and easy to damage neighbouring pads.

Cutting a trace is *not* recommended: you still have to solder to the MCU side of
the cut, and you leave an unexplained cut on the board.

After removal, the four pads you need are VDD, GND, 15 and 16.

> **Power:** the 3.3 V rail was sized for a BT3L (≈25 mA peak). An ESP32 peaks far
> higher. Power the ESP separately and share only ground unless you have measured
> the rail under load.

## Test pads

The board has multiple `TP` pads. They are useful for probing, but their
functions are not documented and vary by revision — verify with a meter before
connecting anything.

## Safety

- Work with the heater unpowered and the burner disconnected.
- Modbus is listen-only for this project. Never connect a TX to that net.
- Check the data line idles at ~3.3 V before wiring an ESP pin to it.
