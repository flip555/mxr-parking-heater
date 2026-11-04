# Firmware notes — ME32F031C8T6

Static analysis of the heater controller image. Everything here is read out of the
decompiled code, not inferred from bus traffic.

## Acquisition

- ST-Link V2, **read-only** — no erase, no option-byte writes, no unlock
- Flash is only visible at the **`0x00000000` alias** on this part; reads at
  `0x08000000` fail
- 64 KB dumped, `0xFF` padding after 65,264 bytes
- sha256 `f8faa572ad733cb7732b3d7e0cd5523c022eed5571801d1ae26344a760f56c4b`
- Option word read as `0x4f410896` (RDP byte `0x96`, not the `0xAA` of a stock F0)
  yet flash read back cleanly — treat as unprotected, do not attempt an unlock

Wrapped as an ELF at base `0x0`, analysed with Ghidra 12.1.4: **125 functions**,
7 strings. The only meaningful string is `vmdizama`.

## Map

| Address | Role |
|---|---|
| `0x5058` | `main` — init, then tick loop |
| `0x477c` | UART RX dispatcher |
| `0x50f0` | Tuya frame sync — shifts bytes looking for `55 AA` |
| `0x4820` | Tuya frame builder `(cmd, len)` |
| `0x47f8` | UART byte transmitter |
| `0x32ec` | Modbus scheduler — poll or write every 10 ticks |
| `0x31f8` | Modbus request builder `(function, register, count)` |
| `0x30b8` | Modbus frame assembly + CRC |
| `0x3de4` | UART TX (busy-wait on TXE) |
| `0x3e84` | Settings-menu handler |
| `0x3828` | Button handling and value clamping |

Main loop calls, on each tick: `0x3828` (buttons), `0x32ec` (Modbus),
`0x3e84` (menu), `0x1e4c` (timers).

## Tuya framing — confirmed

`FUN_00004820(cmd, len)`:

```c
DAT_100003fe = 0x55;
DAT_100003ff = 0xaa;
DAT_10000400 = 0;                        // version
DAT_10000401 = cmd;
DAT_10000402 = len >> 8;                 // big-endian length
DAT_10000403 = len;
uVar1 = FUN_00004f02(&frame, len + 7 - 1);   // additive checksum
frame[len + 7] = uVar1;
FUN_000047f8(&frame, len + 7);           // byte-by-byte TX
```

Matches the documented `55 AA | ver | cmd | len_hi len_lo | payload | sum`.

## Modbus request — confirmed, and the packing is explicit

`FUN_000032ec` decides what to send:

```c
if (DAT_1000003b == 0)  FUN_000031f8(3,    0x4000, 0xe);   // read 14 registers
else                    FUN_000031f8(0x10, 0x3000, 4);    // write 4 registers
```

`FUN_000031f8` builds the write payload:

```c
DAT_1000014e = (count & 0x7f) << 1;                              // byte count = 8
DAT_1000014f = a8 << 4 | a5 << 1 | a4;                           // gear<<4 | mode<<1 | power
DAT_10000150 = a9 << 5 | a6 + 0x10;                              // flag<<5 | setpoint+16
DAT_10000151 = b6;
DAT_10000152 = b8;
```

So register `0x3000` is exactly as documented, and `0x3001` is two flags
(`b6`, `b8`) — which is why it reads `0x0101`.

**New:** bit 5 of the setpoint byte is a separate flag (`a9`). It is zero in all
captured traffic, so `setpoint = byte - 16` works today, but a decoder should mask
it. Meaning not yet determined — likely a unit or override bit.

## Behaviour constants

From `FUN_00003828` (button handling):

```c
if (DAT_100001a8 < 5) { DAT_100001a8++; ... }     // gear: 0..4  -> P1..P5
if (DAT_100001a6 < 0x1e) { DAT_100001a6++; ... }  // setpoint: increments below 30
```

That independently confirms the five-gear range, and suggests the firmware clamps
the setpoint around 30 °C on that path — narrower than the 8–36 the app exposes.

## Datapoint table (flash 0x59aa)

Eight `[id, type]` pairs, indexed by `FUN_00004f20`, validated and dispatched by
`FUN_00004c20` / `FUN_00004cf0`:

| DP | Type | Handler |
|---|---|---|
| 1 | bool | `FUN_00004e4c` |
| 2 | value | `FUN_00004ea0` |
| 3 | value | — |
| 4 | enum | `FUN_00004da4` |
| 5 | enum | `FUN_00004d58` |
| 11 | enum | — |
| 13 | enum | `FUN_00004ecc` |
| 21 | bitmap | — |

Handler behaviour confirms the state model:

```c
// DP4: 0 -> a5=2 (gear), 1 -> a5=0 (AC), 2 -> a5=1 (oil)
// DP5: a8 = value + 1        // gear stored as P-number
```

Those are the same variables the Modbus packer reads, so Tuya DPs and Modbus
registers are two views of one state machine.

Notably **absent**: DP6 and DP7, which a third-party mapping claims are work state
and temperature unit. This firmware does not implement them.

## Report-all map (FUN_000046b0)

Every DP the controller reports, and the variable behind it:

```c
FUN_00005280(1,    DAT_100001a4);   // DP1  bool    power
FUN_000053fc(2,    DAT_100001a6);   // DP2  value   setpoint
FUN_000053fc(3,    DAT_100001cc);   // DP3  value   see note
FUN_000052e4(4,    DAT_100001a5);   // DP4  enum    mode
FUN_000052e4(5,    DAT_100001a9);   // DP5  enum    gear
FUN_000052e4(0xb,  DAT_10000186);   // DP11 enum    work state
FUN_000052e4(0xd,  1);              // DP13 enum    constant 1
FUN_00005338(0x15, _DAT_100001a0);  // DP21 bitmap  fault flags
```

Payload builders:

| Helper | Frame |
|---|---|
| `FUN_00005280` | type 1, len 1 |
| `FUN_000053fc` | type 2, len 4, big-endian |
| `FUN_000052e4` | type 4, len 1 |
| `FUN_00005338` | type 5, variable length |

**DP21 is the fault bitmap** — the menu code tests its bits one at a time
(`&1`, `&2`, `&4`, `&8`, `&0x10`, `&0x20`, `&0x40`, `&0x80`, `&0x100`, `&0x200`,
`&0x800` …) to choose which error message to display.

**DP11 is work state** — compared against `3` in the same menu logic.

**DP13 is a constant `1`** in the report path, so it signals presence/readiness
rather than carrying a value.

**DP3 is ambiguous.** Its variable `DAT_100001cc` is written from the setpoint
variable (`DAT_100001cc = DAT_100001a6`) in one path and zeroed at init in
another. That is either a display mirror of the setpoint or a decompiler
conflation of two distinct addresses. Not resolved.

## Still open

- **The 14 registers at `0x4000`.** The poll is confirmed, but the reply parser
  that unpacks those 28 bytes into RAM has not been located. That is where the
  register meanings live.
- Meaning of flag `a9` (bit 5 of the setpoint byte), and of `b6`/`b8` in `0x3001`.
- Whether the `0x1002xxxx` RAM block is the DP shadow, and how DP ids map onto it.

## Method

```
st-info --probe                     # not needed: identify via OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f0x.cfg \
  -c "adapter speed 500" -c "init" -c "halt" \
  -c "dump_image mcu.bin 0x00000000 0x10000" -c "shutdown"
```

Then wrap as ELF at base `0x0` and analyse. Read-only throughout.
