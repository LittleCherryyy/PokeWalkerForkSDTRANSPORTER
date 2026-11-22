/* Structural gate only. No installation or hardware access. */
#include "walker_wifi_irq_audit.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

int main(void) {
    WalkerWifiIrqLayout p={0x03800000u,0x2000u,0x03801fb0u,0u};
    /* First 17 slots fit, but IRQ_WIFI slot 24 would escape the image. */
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE);
    p.irqTableAddress=0x03801000u;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_INLINE_25_SLOTS_WITHIN_IMAGE);
    /* Runtime table cannot be validated from its address alone. */
    p.runtimeTable=1;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_RUNTIME_TABLE_UNBOUNDED);
    p.runtimeTable=0;
    /* Also reject missing image, unaligned entries, underflow/wraparound. */
    p.arm7ImageBytes=0;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_BAD_ARGUMENT);
    p.arm7ImageBytes=0x2000;
    p.irqTableAddress=0x037fffc0u;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE);
    p.irqTableAddress=0x03800001u;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_BAD_ARGUMENT);
    p.irqTableAddress=0x03801000u;
    p.arm7ImageBytes=17u*4u;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE);
    /* A near-end image still validates only within its provided extent. */
    p.arm7ImageStart=0xfffff000u;
    p.arm7ImageBytes=0x1000u;
    p.irqTableAddress=0xffffff00u;
    assert(walkerWifiIrqInspect(&p)==WALKER_WIFI_IRQ_INLINE_25_SLOTS_WITHIN_IMAGE);
    puts("PASS V7.2.4 IRQ_WIFI: 25-slot footprint audited; runtime table unbounded; no IRQ writes");
    return 0;
}
