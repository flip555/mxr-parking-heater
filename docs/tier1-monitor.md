# Tier 1 — monitor only (no soldering)

Reads the heater's full state and, once a burner is attached, its telemetry. Does
not control anything.

**Hardware:** any ESP8266 (D1 mini) or ESP32.
**Wires:** 3.

## Wiring

Use the 3-pin connector between the controller and the burner.

| ESP | Heater | Notes |
|---|---|---|
| GND | GND | do this first |
| RX | data | D1 mini: the `RX` pin (GPIO3) |
| — | VCC | **not needed** if the ESP has its own supply |

Do **not** connect a TX pin. The controller is the Modbus master; a second talker
corrupts the bus.

Check first: with the heater powered, the data pin should idle at ~3.3 V. If it
sits at 0 V or at 12 V, stop — wrong pin or a level-shift is needed.

## Flash

`esphome/d1mini-modbus-monitor.yaml`

Then open the log. You should see, whenever anything changes:

```
[modbus]: 0x3000: gear=P2 mode=AC power=ON setpoint=21C
```

and once per second the poll (filtered from the log by default):

```
01 03 40 00 00 0E D1 CE
```

## What you get

- Power, mode (AC / gear / oil prime), gear P1–P5, setpoint
- Updates whenever the panel or the app changes anything
- The burner's 14-register telemetry, once a burner answers the poll

## What you don't get

- Control. That needs Tier 2.
- State that has never changed since boot — the bus only reports changes, so the
  ESP starts with defaults until the first event.

## Why this works on a D1 mini

Tier 1 needs exactly one UART (Modbus RX), so the ESP8266's single hardware UART
is enough — no software serial. That also makes it the most reliable variant.
