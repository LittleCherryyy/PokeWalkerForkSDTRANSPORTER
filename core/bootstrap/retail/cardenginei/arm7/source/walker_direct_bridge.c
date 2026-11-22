/* Virtual Pokewalker direct-sync bridge coordinator. GPL-3.0-or-later. */
#include <nds/ndstypes.h>
#include "walker_emu.h"
#include "walker_direct_bridge.h"
#include "walker_directsync.h"

#ifndef TWLSDK
extern u32 walkerControl;

/* Network backend contract. A later DSi transport unit supplies strong
 * definitions. Keeping weak no-op definitions makes this bridge safe in
 * builds where the radio transport has not been linked yet. */
__attribute__((weak)) bool walkerDirectTransportAvailable(void) { return false; }
__attribute__((weak)) int walkerDirectTransportPush(WalkerControl *c) { (void)c; return 0; }
__attribute__((weak)) int walkerDirectTransportPull(WalkerControl *c) { (void)c; return 0; }
__attribute__((weak)) int walkerDirectTransportConfirm(WalkerControl *c) { (void)c; return 0; }

static WalkerControl *directControl(void) {
    WalkerControl *c=(WalkerControl *)walkerControl;
    if(!c || c->magic!=WALKER_MAGIC || c->version!=WALKER_VERSION || !c->cluster) return 0;
    return c;
}

/* Incremental CRC avoids scanning 64 KiB in one VBlank IRQ.
 * At most 512 EEPROM bytes are read per frame while the game is idle.
 * The work is discarded if HGSS modifies the EEPROM during the scan. */
#define WALKER_CRC_BYTES_PER_TICK 512u
static bool crcPending;
static u32 crcSeq, crcOffset, crcState;

static bool durableImageStable(const WalkerControl *c,u32 seq) {
    if(!c || c->magic!=WALKER_MAGIC || c->version!=WALKER_VERSION ||
       c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC || !c->eeprom ||
       c->state || c->writeSeq!=seq || c->flushedSeq!=seq) return false;
    for(unsigned i=0;i<WALKER_SECTORS;i++) if(c->dirty[i]) return false;
    return true;
}

static char hex(unsigned v){return (char)(v<10?'0'+v:'a'+v-10);}

/* The session is generated only after the file is durably committed. This is
 * intentionally deterministic for one running game session; persistent lease
 * storage will replace it in the radio milestone. */
static void makeSession(WalkerControl *c,u32 crc,u32 seq) {
    u32 x=crc ^ seq ^ 0x53444950u;
    for(unsigned n=0;n<WALKER_DIRECT_SESSION_SIZE;n++) {
        x^=x<<13;x^=x>>17;x^=x<<5;
        c->direct.session[n]=hex((x>>(n&7)*4)&15);
    }
    c->direct.session[WALKER_DIRECT_SESSION_SIZE]=0;
    c->direct.trainer[0]=0; /* Android derives and verifies trainer binding. */
}

void walkerDirectBridgeInit(WalkerControl *c) { if(c) walkerDirectBridgeReset(&c->direct,c->flushedSeq); }

/* Called immediately after the ARM7 has physically verified all dirty walker
 * sectors on SD. Never advertise RAM that has not been committed first. */
/* Called after the checked SD writer finishes. Only schedule a CRC here;
 * the actual scan is bounded and performed later in the VBlank tick. */
void walkerDirectBridgeCommitted(WalkerControl *c,u32 seq) {
    if(!durableImageStable(c,seq)) return;
    c->direct.durableSeq=seq;
    if(seq==c->direct.offeredSeq ||
       (crcPending && crcSeq==seq)) return;
    /* A checked-out image must not be replaced by a new offer. */
    if(c->direct.state!=WALKER_DIRECT_IDLE &&
       c->direct.state!=WALKER_DIRECT_PUSH_READY) return;
    crcSeq=seq;
    crcOffset=0;
    crcState=0xffffffffu;
    crcPending=true;
}

static void walkerDirectSnapshotTick(WalkerControl *c) {
    if(!crcPending) return;
    if(!durableImageStable(c,crcSeq) ||
       (c->direct.state!=WALKER_DIRECT_IDLE &&
        c->direct.state!=WALKER_DIRECT_PUSH_READY)) {
        crcPending=false;
        return;
    }
    const u8 *data=(const u8 *)c->eeprom;
    const u32 remaining=WALKER_DIRECT_WALKER_SIZE-crcOffset;
    const u32 count=remaining<WALKER_CRC_BYTES_PER_TICK ?
        remaining : WALKER_CRC_BYTES_PER_TICK;
    for(u32 i=0;i<count;i++) {
        crcState^=data[crcOffset+i];
        for(unsigned bit=0;bit<8;bit++)
            crcState=(crcState>>1)^((0u-(crcState&1u))&0xedb88320u);
    }
    crcOffset+=count;
    if(crcOffset!=WALKER_DIRECT_WALKER_SIZE) return;
    crcPending=false;
    if(!durableImageStable(c,crcSeq)) return;
    c->direct.crc32=~crcState;
    makeSession(c,c->direct.crc32,crcSeq);
    c->direct.offeredSeq=crcSeq;
    c->direct.error=WALKER_DIRECT_ERR_NONE;
    c->direct.attempts=0;
    c->direct.state=WALKER_DIRECT_PUSH_READY;
}

/* Called from VBlank. Backends must be incremental/non-blocking; a return of
 * >0 means complete, 0 means still pending/unavailable, <0 means retryable
 * error. */
void walkerDirectBridgeTick(void) {
    WalkerControl *c=directControl();
    if(!c || c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC) {crcPending=false;return;}
    walkerDirectSnapshotTick(c);
    if(!walkerDirectTransportAvailable()) return;
    int rc=0;
    switch(c->direct.state) {
    case WALKER_DIRECT_PUSH_READY:
    case WALKER_DIRECT_PUSHING:
        c->direct.state=WALKER_DIRECT_PUSHING;
        rc=walkerDirectTransportPush(c);
        if(rc>0){c->direct.state=WALKER_DIRECT_PHONE_OWNS;c->direct.error=0;}
        else if(rc<0){c->direct.state=WALKER_DIRECT_PUSH_READY;c->direct.error=WALKER_DIRECT_ERR_TRANSPORT;c->direct.attempts++;}
        break;
    case WALKER_DIRECT_PULL_READY:
    case WALKER_DIRECT_PULLING:
        c->direct.state=WALKER_DIRECT_PULLING;
        rc=walkerDirectTransportPull(c);
        if(rc>0){c->direct.state=WALKER_DIRECT_CONFIRM_READY;c->direct.error=0;}
        else if(rc<0){c->direct.state=WALKER_DIRECT_PULL_READY;c->direct.error=WALKER_DIRECT_ERR_TRANSPORT;c->direct.attempts++;}
        break;
    case WALKER_DIRECT_CONFIRM_READY:
        rc=walkerDirectTransportConfirm(c);
        if(rc>0){c->direct.state=WALKER_DIRECT_IDLE;c->direct.error=0;}
        else if(rc<0){c->direct.error=WALKER_DIRECT_ERR_TRANSPORT;c->direct.attempts++;}
        break;
    default: break;
    }
}

void walkerDirectBridgeRequestPull(void) {
    WalkerControl *c=directControl();
    if(!c || c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC) return;
    if(c->direct.state==WALKER_DIRECT_PHONE_OWNS) c->direct.state=WALKER_DIRECT_PULL_READY;
}
#else
void walkerDirectBridgeInit(void *c){(void)c;}
void walkerDirectBridgeCommitted(void *c,u32 seq){(void)c;(void)seq;}
void walkerDirectBridgeTick(void){}
void walkerDirectBridgeRequestPull(void){}
#endif
