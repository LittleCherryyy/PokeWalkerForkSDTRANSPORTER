#!/usr/bin/env python3
"""Offline interpretation of a V7.2 ARM7 snapshot (Nintendo DS mode).

Only analyzes user-supplied register values. No hardware, network, ROM,
save or file modification. Never treats an idle timer as proven available.
Sources: libnds nds/interrupts.h, nds/timers.h and DSWifi documentation.
"""
import argparse
import json

INTERRUPTS = {
    0: "VBlank", 1: "HBlank", 2: "VCount",
    3: "Timer 0", 4: "Timer 1", 5: "Timer 2", 6: "Timer 3",
    7: "RTC", 8: "DMA 0", 9: "DMA 1", 10: "DMA 2", 11: "DMA 3",
    12: "Keypad", 16: "IPC sync", 17: "IPC send FIFO",
    18: "IPC receive FIFO", 19: "Game card", 24: "Wi-Fi"
}
DIVIDERS = [1, 64, 256, 1024]

def decode_timer(raw):
    if not 0 <= raw <= 0xffff:
        raise ValueError("timer register must be a 16-bit unsigned integer")
    return {
        "hex": f"0x{raw:04X}",
        "enabled": bool(raw & 0x80),
        "irq_requested": bool(raw & 0x40),
        "cascade": bool(raw & 0x4),
        "prescaler": DIVIDERS[raw & 3],
    }

def analyze(ie, ime, timers):
    if not 0 <= ie <= 0xffffffff or not 0 <= ime <= 0xffffffff:
        raise ValueError("IE and IME must be 32-bit unsigned integers")
    if len(timers) != 4:
        raise ValueError("exactly four ARM7 timer values required")
    details = [decode_timer(t) for t in timers]
    active = [INTERRUPTS.get(bit, f"IRQ bit {bit}") for bit in range(32)
              if ie & (1 << bit)]
    return {
        "cpu": "ARM7",
        "ie": f"0x{ie:08X}",
        "ime": f"0x{ime:08X}",
        "irq_master_enabled": bool(ime & 1),
        "irq_enabled": active,
        "timers": details,
        "wifi_irq_enabled": bool(ie & (1 << 24)),
        "readiness": "NOT VERIFIED",
        "evidence_still_required": [
            "ARM7 DMA3 ownership/activity in DS mode",
            "ARM7 Wi-Fi IRQ dispatcher/handler ownership and chaining",
            "ARM7 DSWifi periodic timer choice and conflict handling",
            "ARM9 timer/IRQ state (especially timer 3) and cooperative context",
            "Safe initialization and shutdown without interrupt/audio/SD regression",
        ],
        "interpretation": (
            "Register snapshot only: disabled timers are not guaranteed free. "
            "Do not invoke Wifi_InitDefault in a retail HGSS IRQ/menu solely "
            "because the displayed TIMER2/3 values are zero."
        ),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ie", required=True, type=lambda s: int(s, 0))
    parser.add_argument("--ime", required=True, type=lambda s: int(s, 0))
    for i in range(4):
        parser.add_argument(f"--timer{i}", required=True,
                            type=lambda s: int(s, 0))
    args = parser.parse_args()
    result = analyze(args.ie, args.ime,
                     [getattr(args, f"timer{i}") for i in range(4)])
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
