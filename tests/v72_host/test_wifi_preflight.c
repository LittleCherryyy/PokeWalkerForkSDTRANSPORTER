/* Offline safety fixtures: NEVER identify simulated ownership with hardware. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_wifi_preflight.h"

static void photographed_dsi(void) {
    WalkerWifiPreflight s;
    memset(&s,0,sizeof(s));
    /* Real photo: ARM9 TIMER3 active 0x00C1, ARM7 DMA3 idle 0;
     * ARM7 Timer0/1 active, and alternative ARM7 timer not validated.
     * Keep all unverified fields at 0 => preflight must refuse Wi-Fi. */
    s.arm9SelectedTimerCr = 0x00C1u;
    s.arm9TimerObserved = 1;
    s.arm7DmaObserved = 1;
    uint32_t flags=walkerWifiPreflight(&s);
    assert(flags & WALKER_WIFI_BLOCK_ARM9_TIMER_ACTIVE);
    assert(flags & WALKER_WIFI_BLOCK_MISSING_CAPTURE);
    assert(flags & WALKER_WIFI_BLOCK_ARM7_TIMER_OWNER);
    assert(flags & WALKER_WIFI_BLOCK_DMA3_OWNER);
    assert(flags & WALKER_WIFI_BLOCK_IRQ_WIFI);
    assert(flags & WALKER_WIFI_BLOCK_ARM9_WORKER);
    assert(flags != 0);
}
static void idle_is_not_ownership(void) {
    WalkerWifiPreflight s;
    memset(&s,0,sizeof(s));
    s.arm9TimerObserved=s.arm7TimerObserved=s.arm7DmaObserved=1;
    uint32_t flags=walkerWifiPreflight(&s);
    assert((flags & WALKER_WIFI_BLOCK_ARM9_TIMER_ACTIVE)==0);
    assert((flags & WALKER_WIFI_BLOCK_MISSING_CAPTURE)==0);
    assert(flags & WALKER_WIFI_BLOCK_ARM9_TIMER_OWNER);
    assert(flags & WALKER_WIFI_BLOCK_ARM7_TIMER_OWNER);
    assert(flags & WALKER_WIFI_BLOCK_DMA3_OWNER);
    assert(flags & WALKER_WIFI_BLOCK_IRQ_WIFI);
    assert(flags != 0);
}
static void each_resource_is_required(void) {
    WalkerWifiPreflight s;
    memset(&s,0,sizeof(s));
    s.arm9TimerObserved=s.arm7TimerObserved=s.arm7DmaObserved=1;
    s.arm9TimerOwnershipVerified=s.arm7TimerOwnershipVerified=1;
    s.arm7Dma3OwnershipVerified=s.arm7WifiIrqChainingVerified=1;
    s.arm7WifiServiceVerified=s.arm9CooperativeWorkerVerified=1;
    /* This is purely synthetic; only an actual hardware ownership audit
     * could ever justify setting all these flags in a device adapter. */
    assert(walkerWifiPreflight(&s)==0);
    s.arm9SelectedTimerCr=0x80;
    assert(walkerWifiPreflight(&s) & WALKER_WIFI_BLOCK_ARM9_TIMER_ACTIVE);
    s.arm9SelectedTimerCr=0;s.arm7SelectedTimerCr=0x80;
    assert(walkerWifiPreflight(&s) & WALKER_WIFI_BLOCK_ARM7_TIMER_ACTIVE);
    s.arm7SelectedTimerCr=0;s.arm7Dma3Cr=0x80000000u;
    assert(walkerWifiPreflight(&s) & WALKER_WIFI_BLOCK_DMA3_ACTIVE);
    assert(walkerWifiPreflight(NULL)==WALKER_WIFI_BLOCK_NO_POLICY);
}
int main(void) {
    photographed_dsi();
    idle_is_not_ownership();
    each_resource_is_required();
    puts("PASS V7.2.3 radio preflight: real photo rejected; idle not ownership; all resources guarded");
    return 0;
}
