# ESP32-C3 heater bridge — board design

A complete 2-layer design for the MXR heater bridge. Everything here is what you
enter into KiCad or EasyEDA; the netlist, BOM and layout rules are the design.

---

## 1. Specification

| Item | Value |
|---|---|
| Board size | 60 × 40 mm (fits the controller compartment) |
| Layers | 2 (top signal, bottom ground pour) |
| Thickness | 1.6 mm |
| Copper | 1 oz (35 µm) |
| Min track | 0.2 mm, signals 0.25 mm |
| Min clearance | 0.2 mm (0.3 mm on 3.3 V) |
| Vias | 0.3 mm drill / 0.6 mm pad |
| Surface finish | HASL lead-free |
| Module | ESP32-C3-MINI-1-N4 (or `-1U` for external antenna) |

### Track widths

| Net class | Width | Why |
|---|---|---|
| 3V3 input from J1 | **0.8 mm** | 350 mA peaks with margin |
| 3V3 distribution | **0.5 mm** | ~1 A at 10 °C rise, 1 oz |
| GND | **pour + 0.5 mm** | plane on bottom layer |
| Signals (UART, I²C, 1-Wire) | **0.25 mm** | |
| USB D+ / D− | **0.2 mm, 90 Ω diff** | ~0.15 mm gap, 1.6 mm FR4 |
| Modbus | **0.3 mm** | single-ended, keep short |

---

## 2. Power tree

```
J1 (controller 3.3V) ──F1 0.5A──► D2 SS14 ──┐
                                            ├──► +3V3 rail
USB-C VBUS ──► U2 AP2112K-3.3 ──────────────┘
```

- **D2** stops the LDO back-feeding the controller rail when USB is plugged in.
- The LDO wins when USB is present (3.3 V vs 3.0 V after the Schottky).
- C1 470 µF sits at the module's 3V3 pad — the C3 pulls ~350 mA peaks on Wi-Fi TX.

---

## 3. Pin assignment

| GPIO | Net | Connector |
|---|---|---|
| IO0 | I2C_SDA | J6 pin 3 |
| IO1 | I2C_SCL | J6 pin 4 |
| IO2 | RF_RX | J5 pin 3 |
| IO3 | NTC_ADC | J8 pin 2 |
| IO4 | TUYA_TX | J2 pin 2 |
| IO5 | TUYA_RX | J2 pin 3 |
| IO6 | MODBUS_RX | J3 pin 2 |
| IO7 | RF_TX | J4 pin 3 |
| IO8 | LED (active low) | LED1 cathode |
| IO9 | BOOT button | SW2 |
| IO10 | ONEWIRE | J7 pin 3 |
| IO18 | USB_D− | J10 |
| IO19 | USB_D+ | J10 |
| IO20 | UART0_RX | J9 pin 4 |
| IO21 | UART0_TX | J9 pin 3 |
| EN | RESET | SW1, R1, C4 |

Strapping pins: **IO2, IO8, IO9**. IO2 is driven by the RF receiver (idles high),
IO8 is pulled high by its internal pull-up and only sinks LED current when driven
low, IO9 has the BOOT button to GND. All safe at reset.

---

## 4. Schematics by block

### Module

- 3V3 → pin 3, GND → pins 1, 2, 11 and the 3×3 thermal grid + pin 49
- EN → R1 10 kΩ to 3V3, C4 100 nF to GND, SW1 to GND
- C2 10 µF + C3 100 nF at 3V3, C1 470 µF nearby

### Connectors

| Ref | Pins | Function |
|---|---|---|
| J1 | 2 | 3.3 V in from controller (F1, D1 TVS on this) |
| J2 | 3 | GND, TUYA_TX (→ module pad 16), TUYA_RX (← pad 15) |
| J3 | 3 | GND, MODBUS_RX, 3V3 (optional feed) |
| J4 | 3 | 3V3, GND, RF_TX |
| J5 | 3 | 3V3, GND, RF_RX |
| J6 | 4 | 3V3, GND, I2C_SDA, I2C_SCL |
| J7 | 3 | 3V3, GND, ONEWIRE |
| J8 | 3 | 3V3, NTC_ADC, GND |
| J9 | 4 | 3V3, GND, UART0_TX, UART0_RX |
| J10 | USB-C | VBUS, GND, D+, D−, CC1, CC2 |

### Passives

- R3, R4: 4.7 kΩ I²C pull-ups to 3V3
- R5: 4.7 kΩ 1-Wire pull-up to 3V3
- R6: 10 kΩ NTC divider, 3V3 → NTC_ADC (probe to GND)
- R7: 1 kΩ LED series to 3V3, cathode to IO8
- R8, R9: 5.1 kΩ CC1/CC2 to GND (USB-C device)
- U3: USBLC6-2SC6 ESD array on D+/D−

---

## 5. Placement

Board outline 60 × 40 mm, USB-C on the short edge.

```
┌──────────────────────────────────────────────┐
│  [J10 USB-C]   U2 LDO   C1 470µF             │
│                                              │
│   ┌─────────────────┐        J1 3V3 (edge)   │
│   │  C3-MINI-1      │                        │
│   │  (antenna edge  │        J3 MODBUS       │
│   │   overhangs)    │                        │
│   └─────────────────┘        J2 TUYA         │
│                                              │
│   SW1  SW2   LED1            J4 RF TX        │
│                              J5 RF RX        │
│   J6 I2C   J7 1-Wire   J8 NTC   J9 UART0     │
└──────────────────────────────────────────────┘
   ▲ keepout: no copper under antenna
```

Rules:

1. **Module antenna overhangs the board edge**; no copper on any layer under the
   keepout rectangle, including the ground pour.
2. **C1, C2, C3 within 5 mm of the module 3V3 pad**, on the same side.
3. **USB D+/D− as a pair**, no stubs, length-matched within 2 mm, reference plane
   continuous underneath (no pour splits).
4. **Tuya UART traces short** (< 30 mm) and away from the LDO switching node.
5. **Modbus** routed on the top layer with ground pour either side; it is
   single-ended and picks up noise easily.
6. **Headers on the edges**, silkscreen-labelled, pin 1 marked.
7. **Thermal grid**: 9 vias under the module GND grid to the bottom pour.

---

## 6. Fabrication

Standard 2-layer, no special requirements. Order 5 boards; the BOM is under £8 in
single quantities.

**Assembly order** (hand-solder friendly):

1. Module (stencil or drag-solder the castellations)
2. LDO, TVS, polyfuse, Schottky
3. Passives 0603, then USB-C
4. Headers last

The antenna keepout makes the module the only part that must be perfectly placed —
everything else tolerates a millimetre of slop.
