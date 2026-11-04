# Tuya MCU protocol

The controller speaks the standard **Tuya MCU serial protocol**. The BT3L module
was a bridge: Tuya BLE on the phone side, this protocol on the heater side. With
the module removed, an ESP32 speaks it directly.

## Link

- **9600 8N1**
- 3.3 V logic
- Controller sends a heartbeat every 15 s

## Frame

```
55 AA | version | command | len_hi len_lo | payload | checksum
```

- `version` is `0x00`
- `len` is big-endian, count of payload bytes
- **checksum** = sum of all preceding bytes, mod 256

## Commands

| Code | Meaning | Direction |
|---|---|---|
| `0x00` | heartbeat | MCU → module |
| `0x01` | product info | MCU → module |
| `0x02` | conf query | MCU ↔ module |
| `0x03` | wifi state | module → MCU |
| `0x04` | reset | MCU → module |
| `0x05` | bulk DP report | MCU → module *(not implemented here)* |
| `0x06` | datapoint deliver (write) | module → MCU |
| `0x07` | datapoint report | MCU → module |
| `0x08` | datapoint query | module → MCU *(reply malformed on this firmware)* |
| `0x10` | obtain DP cache | module → MCU *(not implemented here)* |
| `0x22` | report sync | MCU → module |
| `0x23` | report ack | module → MCU |

## Datapoints

| DP | Type | Meaning | Encoding |
|---|---|---|---|
| 1 | bool | power | `0` / `1` |
| 2 | value | setpoint | 4-byte big-endian, °C, no scaling |
| 3 | value | current temperature | known from third-party mapping, not yet observed |
| 4 | enum | function | `0` gear (UI: Manual), `1` AC/thermostat (UI: Auto), `2` oil prime |
| 5 | enum | gear | `0`–`4` → panel P1–P5 |
| 6 | enum | work state | values unknown |
| 7 | enum | temp unit convert | unknown |

DP type values: `0` raw, `1` bool, `2` value, `3` string, `4` enum, `5` bitmap.

## Captured frames

```
boot heartbeat  55 AA 00 00 00 01 01 01
product info    55 AA 00 01 00 0D 76 6D 64 69 7A 61 6D 61 31 2E 30 2E 30 53   "vmdizama1.0.0"
conf            55 AA 00 02 00 00 01
wifi state      55 AA 00 03 00 00 02
reset           55 AA 00 04 00 00 03

DP1 off         55 AA 00 07 00 05 01 01 00 01 00 0E
DP1 on          55 AA 00 07 00 05 01 01 00 01 01 0F

DP2 = 24        55 AA 00 07 00 08 02 02 00 04 00 00 00 18 2E
DP2 = 25        55 AA 00 07 00 08 02 02 00 04 00 00 00 19 2F

DP4 = 0 gear    55 AA 00 07 00 05 04 04 00 01 00 14
DP4 = 1 AC      55 AA 00 07 00 05 04 04 00 01 01 15
DP4 = 2 oil     55 AA 00 07 00 05 04 04 00 01 02 16

DP5 = 0 (P1)    55 AA 00 07 00 05 05 04 00 01 00 15
DP5 = 1 (P2)    55 AA 00 07 00 05 05 04 00 01 01 16
DP5 = 3 (P4)    55 AA 00 07 00 05 05 04 00 01 03 18

write DP1=1     55 AA 00 06 00 05 01 01 00 01 01 0E
write DP2=18    55 AA 00 06 00 08 02 02 00 04 00 00 00 12 28
write DP4=0     55 AA 00 06 00 05 04 04 00 01 00 13
write DP5=0     55 AA 00 06 00 05 05 04 00 01 00 14
```

Generic write builder used by the ESPHome config:

```cpp
// dp = datapoint id, type = 1 (bool) / 2 (value) / 4 (enum), val = value
uint8_t len = (type == 2) ? 4 : 1;
uint8_t f[16];
f[0]=0x55; f[1]=0xAA; f[2]=0x00; f[3]=0x06;
f[4]=0x00; f[5]=4+len;
f[6]=dp; f[7]=type; f[8]=0x00; f[9]=len;
for (int i=0;i<len;i++) f[10+i] = (val >> (8*(len-1-i))) & 0xFF;
uint8_t s=0; int n=10+len;
for (int i=0;i<n;i++) s+=f[i];
f[n]=s;
```

## Known quirk: the read-all reply

`0x08` (datapoint query) does **not** return the device state on this firmware.
It produces:

```
55 AA 00 07 00 08 00 07 00 04 00 AA 1B 00 05
```

- payload `00 07 00 04 …` decodes to DP id `0`, type `7` — not a valid Tuya type
- the byte in the checksum position is `0x05`; the preceding bytes sum to `0xDE`
- it is **byte-identical** across every state change tested: power, setpoint
  (17–27 °C), mode (0/1/2), gear (P1–P5) and board warming

A brute-force sweep of sum8, xor8 and CRC8 (polys 07/31/9B/39/1D/A7/D5, both
init values, refIn/refOut variants) found no algorithm that validates both this
frame and a known-good DP1 frame.

Conclusion: the frame is a fixed artifact of the controller's report-all path.
Do not build on it.

## Notes

- `0x05` and `0x10` are part of the wider Tuya MCU protocol and are implemented
  by some other devices, but **this** controller ignores `0x10` and never emits
  `0x05`.
- The malformed frame appears to be triggered by the module sending a WiFi-state
  (`0x03`) message.
