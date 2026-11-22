/* Direct DSi sync bridge state shared by the virtual Pokewalker and ARM7.
 * GPL-3.0-or-later.
 *
 * The network backend is deliberately separate from this state machine. The
 * ARM9 emulation only marks the EEPROM dirty. The ARM7 file flusher first
 * commits those bytes to SD, then walkerDirectBridgeTick() may expose the
 * durable image to a transport backend.
 */
#ifndef WALKER_DIRECT_BRIDGE_H
#define WALKER_DIRECT_BRIDGE_H

#include "walker_directsync.h"

#define WALKER_DIRECT_BRIDGE_MAGIC 0x31534450u /* 'PDS1' */

enum {
    WALKER_DIRECT_DISABLED = 0,
    WALKER_DIRECT_IDLE = 1,
    WALKER_DIRECT_PUSH_READY = 2,
    WALKER_DIRECT_PUSHING = 3,
    WALKER_DIRECT_PHONE_OWNS = 4,
    WALKER_DIRECT_PULL_READY = 5,
    WALKER_DIRECT_PULLING = 6,
    WALKER_DIRECT_CONFIRM_READY = 7,
    WALKER_DIRECT_ERROR_STATE = 8
};

enum {
    WALKER_DIRECT_ERR_NONE = 0,
    WALKER_DIRECT_ERR_TRANSPORT = 1,
    WALKER_DIRECT_ERR_PROTOCOL = 2,
    WALKER_DIRECT_ERR_STORAGE = 3,
    WALKER_DIRECT_ERR_CRC = 4
};

#ifndef __ASSEMBLER__
typedef struct WalkerDirectBridge {
    unsigned int magic;
    volatile unsigned int state;
    volatile unsigned int error;
    volatile unsigned int durableSeq;
    volatile unsigned int offeredSeq;
    volatile unsigned int crc32;
    volatile unsigned int attempts;
    volatile unsigned int lastProgress;
    char session[WALKER_DIRECT_SESSION_SIZE + 1];
    char trainer[WALKER_DIRECT_TRAINER_SIZE + 1];
} WalkerDirectBridge;

static inline void walkerDirectBridgeReset(WalkerDirectBridge *d,unsigned durableSeq) {
    if(!d) return;
    d->magic=WALKER_DIRECT_BRIDGE_MAGIC;
    d->state=WALKER_DIRECT_IDLE;
    d->error=WALKER_DIRECT_ERR_NONE;
    d->durableSeq=durableSeq;
    d->offeredSeq=durableSeq;
    d->crc32=0;d->attempts=0;d->lastProgress=0;
    d->session[0]=0;d->trainer[0]=0;
}
#endif

#endif
