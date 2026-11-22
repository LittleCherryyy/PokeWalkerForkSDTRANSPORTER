/* Platform-independent 88-byte direct-sync PING; no socket dependency.
 * No file writes, no .walker or HGSS memory access. GPL-3.0-or-later.
 */
#include "walker_ping_engine.h"
#include <string.h>

static int fail(WalkerPing *p, int error) {
    p->state=WALKER_PING_FAILED;
    p->error=error;
    return p->state;
}

void walkerPingStart(WalkerPing *p, uint32_t frame, uint32_t timeoutFrames) {
    if (!p) return;
    memset(p,0,sizeof(*p));
    if (!timeoutFrames || timeoutFrames > 0x7fffffffu) {
        fail(p,WALKER_PING_ERROR_ARGUMENT);
        return;
    }
    memcpy(p->tx,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE);
    p->tx[8]=WALKER_DIRECT_VERSION;
    p->tx[9]=WALKER_DIRECT_PING;
    /* flags, size, crc, session and trainer are intentionally zero. */
    p->started=frame;
    p->timeoutFrames=timeoutFrames;
    p->state=WALKER_PING_SENDING;
}

void walkerPingCancel(WalkerPing *p) {
    if(p)memset(p,0,sizeof(*p));
}

static int validOk(const WalkerPing *p) {
    const uint8_t *r=p->rx;
    if (memcmp(r,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE)!=0 ||
        r[8]!=WALKER_DIRECT_VERSION || r[9]!=WALKER_DIRECT_OK) return 0;
    /* Android DirectSyncProtocol.write(OP_OK, "", "", null, -1, null)
     * emits exactly an empty 88-byte header with CRC32(empty)==0. */
    if(walkerDirectBe16(r+10)!=0 || walkerDirectBe32(r+12)!=0 ||
       walkerDirectBe32(r+16)!=0) return 0;
    for(unsigned i=20;i<WALKER_DIRECT_HEADER_SIZE;i++)
        if(r[i])return 0;
    return 1;
}

int walkerPingStep(WalkerPing *p, const WalkerPingIo *io, uint32_t frame) {
    if (!p) return WALKER_PING_FAILED;
    if(p->state!=WALKER_PING_SENDING && p->state!=WALKER_PING_RECEIVING)
        return p->state;
    if(!io || !io->send || !io->recv)
        return fail(p,WALKER_PING_ERROR_ARGUMENT);
    /* Unsigned subtraction tolerates frame-counter wraparound. The start
     * routine rejects timeouts longer than half the u32 counter range. */
    if((uint32_t)(frame-p->started)>=p->timeoutFrames)
        return fail(p,WALKER_PING_ERROR_TIMEOUT);
    const unsigned total=WALKER_DIRECT_HEADER_SIZE;
    if(p->state==WALKER_PING_SENDING) {
        const unsigned remaining=total-p->sent;
        int n=io->send(io->user,p->tx+p->sent,remaining);
        if(n<0 || (unsigned)n>remaining) return fail(p,WALKER_PING_ERROR_SEND);
        if(n>0)p->sent+=(unsigned)n;
        if(p->sent==total)p->state=WALKER_PING_RECEIVING;
    } else {
        const unsigned remaining=total-p->received;
        int n=io->recv(io->user,p->rx+p->received,remaining);
        if(n<0 || (unsigned)n>remaining) return fail(p,WALKER_PING_ERROR_RECV);
        if(n>0)p->received+=(unsigned)n;
        if(p->received==total) {
            if(!validOk(p))return fail(p,WALKER_PING_ERROR_REPLY);
            p->state=WALKER_PING_OK;
        }
    }
    return p->state;
}
