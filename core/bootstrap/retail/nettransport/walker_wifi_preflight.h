/* V7.2.3: resource ownership preflight for a future DS-mode Wi-Fi worker.
 * Pure C, no MMIO and no initialization. This gate does NOT grant ownership.
 * GPL-3.0-or-later.
 */
#ifndef WALKER_WIFI_PREFLIGHT_H
#define WALKER_WIFI_PREFLIGHT_H

#include <stdint.h>

/* The integrating code MUST establish each ownership bit independently;
 * values seen in a screenshot are NOT proof that a peripheral is free. */
typedef struct {
    uint16_t arm9SelectedTimerCr;
    uint16_t arm7SelectedTimerCr;
    uint32_t arm7Dma3Cr;
    uint8_t arm9TimerObserved;
    uint8_t arm7TimerObserved;
    uint8_t arm7DmaObserved;
    uint8_t arm9TimerOwnershipVerified;
    uint8_t arm7TimerOwnershipVerified;
    uint8_t arm7Dma3OwnershipVerified;
    uint8_t arm7WifiIrqChainingVerified;
    uint8_t arm7WifiServiceVerified;
    uint8_t arm9CooperativeWorkerVerified;
} WalkerWifiPreflight;

enum {
    WALKER_WIFI_BLOCK_MISSING_CAPTURE = (1u << 0),
    WALKER_WIFI_BLOCK_ARM9_TIMER_ACTIVE = (1u << 1),
    WALKER_WIFI_BLOCK_ARM7_TIMER_ACTIVE = (1u << 2),
    WALKER_WIFI_BLOCK_DMA3_ACTIVE = (1u << 3),
    WALKER_WIFI_BLOCK_ARM9_TIMER_OWNER = (1u << 4),
    WALKER_WIFI_BLOCK_ARM7_TIMER_OWNER = (1u << 5),
    WALKER_WIFI_BLOCK_DMA3_OWNER = (1u << 6),
    WALKER_WIFI_BLOCK_IRQ_WIFI = (1u << 7),
    WALKER_WIFI_BLOCK_ARM7_SERVICE = (1u << 8),
    WALKER_WIFI_BLOCK_ARM9_WORKER = (1u << 9),
    WALKER_WIFI_BLOCK_NO_POLICY = 0xFFFFFFFFu
};

/* Zero means only that the caller supplied a complete, non-conflicting
 * set of assertions. It NEVER establishes real IRQ/DMA/timer ownership.
 * This routine does not enable hardware, allocate memory, or send packets.
 */
uint32_t walkerWifiPreflight(const WalkerWifiPreflight *state);

#endif
