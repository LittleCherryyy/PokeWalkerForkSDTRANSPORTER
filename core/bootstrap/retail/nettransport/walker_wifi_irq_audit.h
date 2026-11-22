/* Nintendo DS-mode ARM7 IRQ_WIFI table footprint audit.
 *
 * Performs ONLY bounds/arithmetic checks. No memory dereference, no IRQ
 * registration, no MMIO, no game-save access. The legacy NTR bootstrap
 * ARM7 hook proves 17 IRQ slots are in its image, but that does not prove
 * slot 24 (IRQ_WIFI) exists or can be safely replaced.
 *
 * A successful footprint check is NOT permission to install an IRQ hook.
 * GPL-3.0-or-later.
 */
#ifndef WALKER_WIFI_IRQ_AUDIT_H
#define WALKER_WIFI_IRQ_AUDIT_H

#include <stdint.h>

#define WALKER_WIFI_IRQ_SLOT 24u
#define WALKER_WIFI_IRQ_REQUIRED_ENTRIES (WALKER_WIFI_IRQ_SLOT+1u)

typedef struct {
    uint32_t arm7ImageStart; /* only the verified loaded ARM7 image */
    uint32_t arm7ImageBytes;
    uint32_t irqTableAddress; /* address derived from verified IRQ signature */
    uint32_t runtimeTable; /* 0: inline image; 1: externally allocated */
} WalkerWifiIrqLayout;

typedef enum {
    WALKER_WIFI_IRQ_BAD_ARGUMENT=1,
    WALKER_WIFI_IRQ_RUNTIME_TABLE_UNBOUNDED=2,
    WALKER_WIFI_IRQ_INLINE_TABLE_OUTSIDE_IMAGE=3,
    WALKER_WIFI_IRQ_INLINE_25_SLOTS_WITHIN_IMAGE=4
} WalkerWifiIrqFootprint;

WalkerWifiIrqFootprint walkerWifiIrqInspect(const WalkerWifiIrqLayout *layout);

/* Footprint classification is intentionally NEVER sufficient to install.
 * The driver still needs verified table ownership, compatible IRQ dispatch,
 * proof of original handler chaining, and a cooperative shutdown path.
 */
#endif
