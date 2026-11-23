#include "walker_wifi_irq_audit.h"

WalkerWifiIrqFootprint walkerWifiIrqInspect(const WalkerWifiIrqLayout *p) {
    if (!p || !p->arm7ImageBytes || (p->arm7ImageStart & 3u) ||
        (p->irqTableAddress & 3u))
        return WALKER_WIFI_IRQ_BAD_ARGUMENT;

    /* The existing NTR hook uses a separate DSi runtime-table layout
     * (returnIndex==3). Its image doesn't contain the table. An address
     * in ARM7 RAM is not proof that 25 entries are allocated or writable. */
    if (p->runtimeTable)
        return WALKER_WIFI_IRQ_RUNTIME_TABLE_UNBOUNDED;

    /* Avoid wrapping 32-bit ranges. The original bootstrap validated only
     * 17 entries: enough for VBlank slot 0 and IPC slot 16. */
    const uint32_t required=WALKER_WIFI_IRQ_REQUIRED_ENTRIES * 4u;
    if (p->arm7ImageBytes < required)
        return WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE;
    if (p->irqTableAddress < p->arm7ImageStart)
        return WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE;
    const uint32_t offset=p->irqTableAddress-p->arm7ImageStart;
    if (offset > p->arm7ImageBytes-required)
        return WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE;
    return WALKER_WIFI_IRQ_INLINE_25_SLOTS_WITHIN_IMAGE;
}
