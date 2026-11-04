# Modbus RTU protocol

The controller talks to the burner over a **single-wire, half-duplex UART** using
**Modbus RTU**. It is the Modbus **master** and polls once per second.

This bus is the best source of live state: the controller mirrors every settings
change onto it, and the burner answers with telemetry.

## Link

- **9600 8N1**, 3.3 V logic
- 3-pin connector: GND, VCC, one data line
- Single wire → both ends drive it; you can only listen
- Standard Modbus CRC-16 (poly `0xA001`, init `0xFFFF`), transmitted low byte first

## Controller → burner: state write

Sent whenever power, mode, gear or setpoint changes (from the panel or from a
Tuya datapoint write).

```
01 10 30 00 00 04 08 31 28 01 01 00 00 00 00 A1 41
│  │  │     │  │  └─ 8 data bytes (4 registers)   └─ CRC
│  │  │     │  └──── byte count = 8
│  │  │     └─────── register count = 4
│  │  └───────────── start register 0x3000
│  └──────────────── function 0x10 = write multiple registers
└─────────────────── slave 1
```

### Register 0x3000 — state word

```
byte 0 (0x3000 high) : gear << 4 | (mode << 1) | power
byte 1 (0x3000 low)  : setpoint + 16
```

`mode` is 2 bits:

| mode | meaning |
|---|---|
| 0 | AC / thermostat |
| 1 | manual oil prime |
| 2 | gear |

Full low nibble:

| Nibble | Mode | Power |
|---|---|---|
| `0x0` | AC | off |
| `0x1` | AC | on |
| `0x2` | oil prime | off |
| `0x3` | oil prime | on |
| `0x4` | gear | off |
| `0x5` | gear | on |

Worked examples (bytes after `01 10 30 00 00 04 08`):

| Frame | Gear | Mode | Power | Setpoint |
|---|---|---|---|---|
| `21 25 …` | P2 | AC | on | 21 °C |
| `25 25 …` | P2 | Gear | on | 21 °C |
| `15 25 …` | P1 | Gear | on | 21 °C |
| `35 25 …` | P3 | Gear | on | 21 °C |
| `45 1F …` | P4 | Gear | on | 15 °C |
| `23 2C …` | P2 | oil prime | on | 28 °C |
| `12 29 …` | P1 | oil prime | **off** | 25 °C |
| `20 29 …` | P2 | AC | **off** | 25 °C |

Registers `0x3001`–`0x3003` observed as `0x0101 0x0000 0x0000`, not yet decoded.

## Controller → burner: poll

Once per second:

```
01 03 40 00 00 0E D1 CE
│  │  │     │     └─ CRC 0xCED1
│  │  │     └─────── 14 registers
│  │  └───────────── start register 0x4000
│  └──────────────── function 3 = read holding registers
└─────────────────── slave 1
```

Unanswered when no burner is attached.

## Burner → controller: reply

Expected once a burner is present:

```
01 03 1C <28 bytes> <CRC>
```

14 registers × 2 bytes. **Contents not yet mapped** — the main open item in this
project. It should contain fan, pump, flame state, probes and fault bits.

## Listening safely

The controller is the master and owns the timing. Do **not** transmit: Modbus RTU
has no collision handling, and a second talker corrupts both the poll and the
burner's reply.

One extra listener is harmless. That is what this project does.

## Decoding tips

- Poll and reply both start `01 03`; distinguish by what follows — poll has
  `40 00 00 0E`, reply has `1C` as the byte count.
- Validate the CRC before trusting a frame. On a software UART this is what makes
  occasional corruption harmless: the next poll arrives in one second.
- Split bursts on a ~20 ms inter-frame gap.
