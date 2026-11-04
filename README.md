# MXR Parking Heater — ESPHome bridge

Local control and monitoring for a **MaXpeedingRods (MXR) Tuya parking heater**
without the phone app, the cloud, or the original BLE module.

The heater controller is a Tuya MCU device. The factory BT3L module is only a
BLE-to-UART bridge, so an ESP32 can take its place on the UART and speak the same
protocol. A second, simpler bus (Modbus RTU) exposes the heater's live state.

> Status: working on hardware. Control, state mirroring and persistence are
> verified. The burner telemetry block is documented but **not yet mapped** —
> see [Unknowns](#unknowns).

---

## Two ways to use this

| | Tier 1 — Monitor | Tier 2 — Full control |
|---|---|---|
| Soldering | **none** | BT3L module removed |
| Wires | 3 | 4 |
| Control from HA | ✗ | ✓ |
| State + telemetry | ✓ | ✓ |
| Difficulty | beginner | intermediate |

Start with Tier 1. It needs no disassembly and proves the wiring before you
commit to removing anything.

---

## How it works

```
                 ┌──────────────┐
   phone app ────┤  BT3L (BLE)  │   ← removed in Tier 2
                 └──────┬───────┘
                        │ UART 55AA (Tuya MCU protocol)
  ESP32 ────────────────┤
                        │
                 ┌──────┴───────┐
                 │ ME32F031C8T6 │  heater controller
                 └──────┬───────┘
                        │ single-wire UART, Modbus RTU
                 ┌──────┴───────┐
                 │    burner    │  fan, pump, flame, probes
                 └──────────────┘
```

Two independent paths to the same state:

- **Tuya MCU protocol** (`55 AA …`) — how you *change* settings. Datapoint writes.
- **Modbus RTU** — how you *read* state. The controller polls its burner once a
  second and mirrors every state change onto the bus.

Neither bus can read the full state on demand: the Tuya "read all" reply on this
firmware is malformed, and the Modbus poll is only answered by a connected
burner. The ESP therefore keeps its own persisted copy and treats both buses as
corrections.

Details: [Tuya protocol](docs/protocol-tuya.md) ·
[Modbus protocol](docs/protocol-modbus.md)

---

## Hardware

- **Controller:** ME32F031C8T6 (MESILICON, Cortex-M0)
- **BLE module:** Tuya BT3L (TLSR8250) — removed for Tier 2
- **Recommended bridge:** any ESP32 (2+ hardware UARTs)
- **Also works:** ESP8266 / D1 mini for Tier 1 (single UART is enough)

Full teardown, pinouts and removal notes: [docs/hardware.md](docs/hardware.md)

---

## Quick start

### Tier 1 — monitor only

Wire to the 3-pin connector between controller and burner:

| ESP | Heater |
|---|---|
| GND | GND |
| RX (GPIO3 on a D1 mini) | data |
| 3V3 | VCC *(optional — see caveat)* |

Flash [`esphome/d1mini-modbus-monitor.yaml`](esphome/d1mini-modbus-monitor.yaml).

You get power, mode, gear and setpoint, decoded from the controller's own
Modbus writes — plus the burner's telemetry once one is attached.

### Tier 2 — full control

Remove the BT3L module, then:

| ESP32 | Heater |
|---|---|
| GND | GND |
| GPIO16 (RX) | BT3L pad 15 — MCU TX |
| GPIO17 (TX) | BT3L pad 16 — MCU RX |
| GPIO25 (RX) | Modbus data |
| 3V3 | VCC *(see caveat)* |

Flash [`esphome/mxr-esp32-control.yaml`](esphome/mxr-esp32-control.yaml).

Step-by-step: [Tier 1](docs/tier1-monitor.md) · [Tier 2](docs/tier2-control.md)

> **Power caveat:** the controller's 3.3 V rail is sized for a BT3L (~25 mA).
> An ESP32 peaks far higher. Power the ESP separately and share only ground
> unless you have measured the rail under load.

---

## What works

- Power on/off, mode (Manual / Auto / Oil prime), gear P1–P5, setpoint
- State survives ESP reboots (globals + flash)
- State corrections from both the panel and the Tuya bus
- Modbus decoder for every controller state change

## Unknowns

- **Burner telemetry (`0x4000`, 14 registers)** — the block exists and is polled
  at 1 Hz, but is only answered when a burner is attached. Not yet mapped.
- **Tuya read-all (`0x08`)** — returns one DP1 report plus a fixed malformed
  frame. The `0x10` (obtain DP cache) command is not implemented by this
  firmware.
- Current-temperature and work-state DPs are known for this product from a
  third-party Tuya BLE mapping (DP3 and DP6) but have not been observed here.

---

## References

- Product key: `vmdizama`, firmware `1.0.0`
- Tuya MCU serial protocol (public SDK)
- Modbus RTU specification

## Licence

MIT — see [LICENSE](LICENSE).
