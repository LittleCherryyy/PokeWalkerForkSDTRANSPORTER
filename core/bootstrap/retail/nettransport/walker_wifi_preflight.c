/* Defensive fail-closed resource validation for future resident Wi-Fi.
 * No MMIO, libnds, DSWifi, radio init, timers, DMA, or game/save access.
 */
#include "walker_wifi_preflight.h"

uint32_t walkerWifiPreflight(const WalkerWifiPreflight *s) {
    if (!s) return WALKER_WIFI_BLOCK_NO_POLICY;
    uint32_t blocked = 0;
    if (!s->arm9TimerObserved || !s->arm7TimerObserved ||
        !s->arm7DmaObserved)
        blocked |= WALKER_WIFI_BLOCK_MISSING_CAPTURE;

    /* Bit 7 of NDS TIMER_CR is the enable bit; DMA3 bit 31 is enable. */
    if (s->arm9SelectedTimerCr & 0x80u)
        blocked |= WALKER_WIFI_BLOCK_ARM9_TIMER_ACTIVE;
    if (s->arm7SelectedTimerCr & 0x80u)
        blocked |= WALKER_WIFI_BLOCK_ARM7_TIMER_ACTIVE;
    if (s->arm7Dma3Cr & 0x80000000u)
        blocked |= WALKER_WIFI_BLOCK_DMA3_ACTIVE;

    if (!s->arm9TimerOwnershipVerified)
        blocked |= WALKER_WIFI_BLOCK_ARM9_TIMER_OWNER;
    if (!s->arm7TimerOwnershipVerified)
        blocked |= WALKER_WIFI_BLOCK_ARM7_TIMER_OWNER;
    if (!s->arm7Dma3OwnershipVerified)
        blocked |= WALKER_WIFI_BLOCK_DMA3_OWNER;
    if (!s->arm7WifiIrqChainingVerified)
        blocked |= WALKER_WIFI_BLOCK_IRQ_WIFI;
    /* Structural table size proof must precede any IRQ_WIFI installation.
     * Even an in-image 25-slot range does not prove handler ownership. */
    if (walkerWifiIrqInspect(&s->irqLayout) !=
            WALKER_WIFI_IRQ_INLINE_25_SLOTS_WITHIN_IMAGE)
        blocked |= WALKER_WIFI_BLOCK_IRQ_TABLE_UNVERIFIED;
    if (!s->arm7WifiServiceVerified)
        blocked |= WALKER_WIFI_BLOCK_ARM7_SERVICE;
    if (!s->arm9CooperativeWorkerVerified)
        blocked |= WALKER_WIFI_BLOCK_ARM9_WORKER;
    return blocked;
}
