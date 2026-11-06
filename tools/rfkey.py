#!/usr/bin/env python3
"""Generate 433 MHz keyfob frames for the MXR / MaXpeedingRods heater.

The remote is a fixed-code EV1527-style encoder at 24 bits:

    20-bit address + 4-bit button, MSB first

Timing captured from a real remote (receiver-stretched values, which is what
the controller actually accepts):

    1    = 1060 us high, 260 us low
    0    =  400 us high, 930 us low
    sync =  390 us high, 10300 us low

Usage:
    python3 rfkey.py --random
    python3 rfkey.py --id 0x5EED1
    python3 rfkey.py --id 01011110111011010001

Writes a YAML block to stdout: substitutions + rc_switch buttons, and the
raw-code arrays as a fallback for firmware where rc_switch timings don't match.
"""

import argparse
import secrets
import sys

BUTTONS = [("Power On", 0x2), ("Power Off", 0x8), ("Temp Up", 0x1), ("Temp Down", 0x4)]

SYNC = (390, -10300)
ONE = (1060, -260)
ZERO = (400, -930)


def parse_id(value: str) -> int:
    v = value.strip()
    if v.lower().startswith("0x"):
        n = int(v, 16)
        bits = 20
    elif set(v) <= {"0", "1"} and len(v) == 20:
        n = int(v, 2)
        bits = 20
    else:
        raise argparse.ArgumentTypeError(
            "ID must be 20 binary digits or a hex value (e.g. 0x5EED1)"
        )
    if not 0 < n < (1 << bits):
        raise argparse.ArgumentTypeError("ID must be 1..0xFFFFF (20 bits)")
    return n


def frame_bits(id20: int, button: int) -> str:
    return f"{id20:020b}{button:04b}"


def raw_code(bits: str) -> list[int]:
    out = list(SYNC)
    for b in bits:
        out.extend(ONE if b == "1" else ZERO)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--random", action="store_true", help="generate a random 20-bit ID")
    g.add_argument("--id", type=parse_id, help="20-bit ID as hex or binary")
    args = ap.parse_args()

    id20 = secrets.randbelow((1 << 20) - 1) + 1 if args.random else args.id
    id_bits = f"{id20:020b}"

    print(f"# RF keyfob ID: 0x{id20:05X}  ({id_bits})")
    print("# Pair it via the controller's OC1 menu: press one button twice.")
    print()
    print("substitutions:")
    print(f'  rf_id: "{id_bits}"')
    print()
    print("button:")

    for name, btn in BUTTONS:
        bits = frame_bits(id20, btn)
        print(f'  - platform: template')
        print(f'    name: "{name}"')
        print(f'    on_press:')
        print(f'      - remote_transmitter.transmit_rc_switch_raw:')
        print(f'          code: "{bits}"')
        print(f'          protocol: 1')
        print(f'          repeat: {{ times: 6, wait_time: 5ms }}')
        print(f'      - delay: 150ms')
        print(f'      - remote_transmitter.transmit_rc_switch_raw:')
        print(f'          code: "{bits}"')
        print(f'          protocol: 1')
        print(f'          repeat: {{ times: 6, wait_time: 5ms }}')
        print()

    print("# --- fallback: raw timings (if rc_switch protocol 1 is rejected) ---")
    for name, btn in BUTTONS:
        arr = ", ".join(str(v) for v in raw_code(frame_bits(id20, btn)))
        print(f"# {name} (0x{btn:X})")
        print(f"# [{arr}]")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
