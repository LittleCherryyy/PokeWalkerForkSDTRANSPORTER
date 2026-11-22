/* V7.2.2 ARM9 pre-menu register snapshot.
 * Passed as the fourth ARM9 register argument (r3) from resident NTR
 * cardengine into the separately loaded IGM. No shared mailbox offsets
 * or cardengine C/ASM layouts are modified. GPL-3.0-or-later.
 */
#ifndef WALKER_ARM9_SNAPSHOT_H
#define WALKER_ARM9_SNAPSHOT_H

#include <nds/ndstypes.h>

#define WALKER_ARM9_SNAPSHOT_MAGIC 0x32504D57u /* WMP2 */

typedef struct {
    u32 magic;
    u32 timer3;
    u32 ie;
    u32 ime;
    /* V7.8: observations captured at entry of the original ARM9 cardRead,
     * never from an IRQ handler or Wi-Fi. This extends, not reorders, V7.2.
     * Counts may stay zero in gameplay without cartridge reads. */
    u32 romReadCalls;
    u32 eligibleReadCalls;
    u32 lastReadCpsrMode;
    u32 lastReadIme;
    /* V7.9 bounded simulated scheduling: observed only at the END of a
     * completed normal cardRead callback, not at its start. An in-game
     * menu exit queues one dry-run; the next eligible completion consumes
     * it by updating counters. No network or save I/O is performed. */
    u32 postReadEligibleCalls;
    u32 dryRunQueued;
    u32 dryRunDone;
    u32 dryRunPending;
} WalkerArm9Snapshot;

#endif
