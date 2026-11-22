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
} WalkerArm9Snapshot;

#endif
