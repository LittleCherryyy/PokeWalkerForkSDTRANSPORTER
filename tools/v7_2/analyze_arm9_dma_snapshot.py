#!/usr/bin/env python3
"""Conservative decoding of photographed V7.2.1 ARM7 DMA3 + ARM9-menu state.

Read-only; no console access, no sockets or game/save data. The ARM7 DMA
snapshot was taken before the menu pause, but ARM9 IE/IME/TMR3 are read
AFTER the in-game menu entered its critical section. Never infer ownership.
"""
import argparse
import json

_IRQ_BITS = {
    0: "VBlank", 1: "HBlank", 2: "VCount",
    3: "Timer 0", 4: "Timer 1", 5: "Timer 2", 6: "Timer 3",
    8: "DMA 0", 9: "DMA 1", 10: "DMA 2", 11: "DMA 3",
    12: "Keypad", 16: "IPC sync", 17: "IPC send FIFO",
    18: "IPC receive FIFO", 19: "Game card", 21: "Geometry FIFO",
}
_DIVIDERS=(1,64,256,1024)

def analyze(dma_control, dma_src, dma_dst, arm9_timer3, arm9_ie, arm9_ime):
    vals=(dma_control,dma_src,dma_dst,arm9_ie,arm9_ime)
    if any(not 0 <= x <= 0xffffffff for x in vals):
        raise ValueError("DMA and ARM9 interrupt registers must be 32-bit unsigned")
    if not 0 <= arm9_timer3 <= 0xffff:
        raise ValueError("ARM9 TIMER3_CR must be 16-bit unsigned")
    dma_enabled=bool(dma_control & (1<<31))
    timer_enabled=bool(arm9_timer3 & 0x80)
    timer_irq=bool(arm9_timer3 & 0x40)
    interrupts=[_IRQ_BITS.get(bit, f"IRQ bit {bit}") for bit in range(32)
                if arm9_ie & (1<<bit)]
    return {
        "arm7_dma3": {
            "control":f"0x{dma_control:08X}",
            "source":f"0x{dma_src:08X}",
            "destination":f"0x{dma_dst:08X}",
            "enabled_at_pre_menu_snapshot":dma_enabled,
            "ownership_verified":False,
        },
        "arm9": {
            "context":"IN GAME MENU (after critical section)",
            "timer3_control":f"0x{arm9_timer3:04X}",
            "timer3_enabled":timer_enabled,
            "timer3_irq_configured":timer_irq,
            "timer3_prescaler":_DIVIDERS[arm9_timer3 & 3],
            "irq_mask":f"0x{arm9_ie:08X}",
            "irq_mask_sources":interrupts,
            "irq_master_enabled_in_menu":bool(arm9_ime & 1),
            "gameplay_irq_master_state":"NOT CAPTURED",
        },
        "dswifi_timer3_default_compatibility": (
            "BLOCKED: ARM9 timer 3 configured as active in menu; "
            "do not overwrite the existing timer or IRQ handler."
            if timer_enabled else
            "UNVERIFIED: idle in-menu timer does not prove safe ownership."
        ),
        "wifi_resident_ready":False,
        "required_before_radio_start":[
            "ARM9 pre-menu timer and IRQ snapshot, captured before critical section",
            "ARM9 Timer 3 scheduling ownership and IRQ handler chain",
            "ARM7 DMA3 ownership over the full gameplay lifecycle",
            "ARM7 IRQ_WIFI slot 24 and DSWifi periodic timer service",
            "Non-blocking ARM9 cooperative execution and safe shutdown",
        ],
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("dma-cr","dma-src","dma-dst","arm9-timer3","arm9-ie","arm9-ime"):
        p.add_argument("--"+key,required=True,type=lambda s:int(s,0))
    a=p.parse_args()
    d=analyze(a.dma_cr,a.dma_src,a.dma_dst,a.arm9_timer3,a.arm9_ie,a.arm9_ime)
    print(json.dumps(d,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
