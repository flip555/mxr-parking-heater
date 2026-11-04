# Tier 2 — full control (BT3L removed)

Replaces the BLE module with an ESP32: commands go out on the Tuya UART, state
comes back on both the Tuya UART and the Modbus bus.

**Hardware:** ESP32 (two hardware UARTs). An ESP8266 can work but puts one bus on
software serial — see the note at the end.
**Wires:** 4.

## 1. Remove the BT3L

See [hardware.md](hardware.md#removing-the-bt3l-tier-2-only). Hot air is easiest.
You need the VDD, GND, pin 15 and pin 16 pads afterwards.

## 2. Wiring

| ESP32 | Heater | Purpose |
|---|---|---|
| GND | GND | common ground |
| GPIO16 (RX) | BT3L pad 15 (MCU TX) | Tuya receive |
| GPIO17 (TX) | BT3L pad 16 (MCU RX) | Tuya transmit |
| GPIO25 (RX) | Modbus data | state + telemetry |

ESP32 UART2 defaults to 16/17, so this costs no extra configuration.

## 3. Flash

`esphome/mxr-esp32-control.yaml`

On first boot the ESP waits for WiFi, restores its stored state, and — if it has
never been calibrated — runs a calibration: **mode AC, gear P1, 18 °C**.

## 4. Calibrate once

The controller cannot be asked for its state (its "read all" reply is malformed),
so the ESP keeps its own copy. Calibration puts the heater into a known state,
after which everything tracks.

Press **Calibrate Heater** in HA, or let it run on first boot. After that:

- panel changes → Tuya DP report + Modbus mirror → ESP updates
- HA changes → Tuya DP write → controller applies → Modbus mirror confirms
- ESP reboot → last state restored from flash, nothing transmitted until boot
  completes

## Why writes are suppressed at boot

Template entities publish their restored state during setup. Without suppression
that would send a datapoint write on every boot and stomp the heater back to
whatever the ESP remembered. `dp_suppress` starts `true` and is cleared a few
seconds after boot, after the static state has been published.

## Oil prime

`Primer` runs for a configurable number of seconds, then restores the previous
mode. It is a momentary function, not a mode: the controller returns to its
previous setting when stopped.

## If you must use an ESP8266

Put the **Tuya bus on the hardware UART** and Modbus on software serial. Modbus is
the forgiving one — 1 Hz, short frames, CRC-checked — so a dropped frame costs one
second, not a failed command.
